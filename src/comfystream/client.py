import asyncio
import gc
from typing import List
import logging
import torch
import av 
import numpy as np

from comfystream import tensor_cache
from comfystream.utils import convert_prompt

from comfy.api.components.schema.prompt import PromptDictInput
from comfy.cli_args_types import Configuration
from comfy.client.embedded_comfy_client import EmbeddedComfyClient
from comfy import model_management

logger = logging.getLogger(__name__)


class ComfyStreamClient:
    def __init__(self, max_workers: int = 1, **kwargs):
        config = Configuration(**kwargs)
        self.comfy_client = EmbeddedComfyClient(config, max_workers=max_workers)
        self.running_prompts = {} # To be used for cancelling tasks
        self.current_prompts = []
        self.cleanup_lock = asyncio.Lock()
        self._prompt_update_lock = asyncio.Lock()
        self.error_queue = asyncio.Queue()
        self._error_monitor_task = None

    async def start_error_monitor(self):
        """Start monitoring for errors in the error queue."""
        if self._error_monitor_task is None:
            self._error_monitor_task = asyncio.create_task(self._monitor_errors())

    async def stop_error_monitor(self):
        """Stop monitoring for errors."""
        if self._error_monitor_task is not None:
            self._error_monitor_task.cancel()
            try:
                await self._error_monitor_task
            except asyncio.CancelledError:
                pass
            self._error_monitor_task = None

    async def _monitor_errors(self):
        """Monitor the error queue and log errors."""
        while True:
            try:
                error = await self.error_queue.get()
                logger.error(f"Error in ComfyStreamClient: {error}")
                self.error_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in error monitor: {e}")

    async def report_error(self, error: Exception):
        """Report an error to the error queue."""
        await self.error_queue.put(error)

    async def set_prompts(self, prompts: List[PromptDictInput]):
        await self.cancel_running_prompts()
        self.current_prompts = [convert_prompt(prompt) for prompt in prompts]
        for idx in range(len(self.current_prompts)):
            task = asyncio.create_task(self.run_prompt(idx))
            self.running_prompts[idx] = task

    async def update_prompts(self, prompts: List[PromptDictInput]):
        async with self._prompt_update_lock:
            # TODO: currently under the assumption that only already running prompts are updated
            if len(prompts) != len(self.current_prompts):
                raise ValueError(
                    "Number of updated prompts must match the number of currently running prompts."
                )
            # Validation step before updating the prompt, only meant for a single prompt for now
            for idx, prompt in enumerate(prompts):
                converted_prompt = convert_prompt(prompt)
                try:
                    await self.comfy_client.queue_prompt(converted_prompt)
                    self.current_prompts[idx] = converted_prompt
                except Exception as e:
                    raise Exception(f"Prompt update failed: {str(e)}") from e

    async def run_prompt(self, prompt_index: int):
        while True:
            async with self._prompt_update_lock:
                try:
                    await self.comfy_client.queue_prompt(self.current_prompts[prompt_index])
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    await self.report_error(e)
                    await self.cleanup()
                    logger.error(f"Error running prompt: {str(e)}")
                    raise

    async def warm_video(self, WARMUP_RUNS: int = 5, width: int = 512, height: int = 512):
        """Warm up the video processing pipeline with dummy frames."""
        # Create dummy frame with the CURRENT resolution settings
        dummy_frame = av.VideoFrame()
        dummy_frame.side_data.input = torch.randn(1, height, width, 3)
        
        logger.info(f"Warming video pipeline with resolution {width}x{height}")

        for _ in range(WARMUP_RUNS):
            self.put_video_input(dummy_frame)
            await self.get_video_output()

    async def warm_audio(self, WARMUP_RUNS: int = 5, sample_rate: int = 48000, buffer_size: int = 48000):
        """Warm up the audio processing pipeline with dummy frames."""
        dummy_frame = av.AudioFrame()
        dummy_frame.side_data.input = np.random.randint(-32768, 32767, int(48000 * 0.5), dtype=np.int16)   # TODO: adds a lot of delay if it doesn't match the buffer size, is warmup needed?
        dummy_frame.sample_rate = 48000

        for _ in range(WARMUP_RUNS):
            self.put_audio_input(dummy_frame)
            await self.get_audio_output()

    async def cleanup(self, exit_client: bool = False):
        """Clean up all resources and stop all tasks."""
        async with self.cleanup_lock:
            try:
                logger.info("Starting client cleanup")

                # First cancel all running prompts without acquiring the lock again
                await self.cancel_running_prompts(use_lock=False)
                self.current_prompts.clear()
                
                # Clean up queues with timeout
                try:
                    await asyncio.wait_for(self.cleanup_queues(), timeout=5.0)
                except asyncio.TimeoutError:
                    await self.report_error(Exception("Timeout while cleaning up queues"))
                except Exception as e:
                    await self.report_error(e)
                
                # Finally unload all models with timeout
                try:
                    await asyncio.wait_for(self.unload_all_models(), timeout=3.0)
                    logger.info("Successfully unloaded all models")
                except asyncio.TimeoutError:
                    await self.report_error(Exception("Timeout while unloading models"))
                except Exception as e:
                    await self.report_error(e)
                
                # Optionally fully exit the client
                if exit_client and self.comfy_client.is_running:
                    # Dispose of the comfy_client
                    if hasattr(self, 'comfy_client') and self.comfy_client.is_running:
                        try:
                            await asyncio.wait_for(
                                self.comfy_client.__aexit__(),
                                timeout=5.0
                            )
                        except asyncio.TimeoutError:
                            await self.report_error(Exception("Timeout while disposing comfy_client"))
                        except Exception as e:
                            await self.report_error(e)

                logger.info("Client cleanup complete")
            except Exception as e:
                await self.report_error(e)
                raise

    async def cancel_running_prompts(self, use_lock: bool = True):
        """Cancel all running prompt tasks."""
        async def _cancel():
            tasks_to_cancel = list(self.running_prompts.values())
            for task in tasks_to_cancel:
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=0.5)  # Add timeout for task cancellation
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                except Exception as e:
                    logger.error(f"Error cancelling task: {e}")
            self.running_prompts.clear()

        if use_lock:
            async with self.cleanup_lock:
                await _cancel()
        else:
            await _cancel()

    async def cleanup_queues(self):
        """Clean up all queues and dispose of the comfy_client."""
        try:
            # Clear queues and move CUDA tensors to CPU before discarding
            while not tensor_cache.image_inputs.empty():
                try:
                    tensor = tensor_cache.image_inputs.get_nowait()
                    if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                        tensor.cpu()
                except Exception as e:
                    logger.error(f"Error clearing image inputs queue: {e}")

            while not tensor_cache.audio_inputs.empty():
                try:
                    tensor = tensor_cache.audio_inputs.get_nowait()
                    if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                        tensor.cpu()
                except Exception as e:
                    logger.error(f"Error clearing audio inputs queue: {e}")

            # Use asyncio.wait_for to prevent hanging on queue cleanup
            try:
                while not tensor_cache.image_outputs.empty():
                    try:
                        tensor = await asyncio.wait_for(
                            tensor_cache.image_outputs.get_nowait(),
                            timeout=1.0
                        )
                        if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                            tensor.cpu()
                    except asyncio.TimeoutError:
                        logger.warning("Timeout while clearing image outputs queue")
                        break
                    except asyncio.QueueEmpty:
                        break
                    except Exception as e:
                        logger.error(f"Error clearing image outputs queue: {e}")
            except Exception as e:
                logger.error(f"Error during image outputs queue cleanup: {e}")

            try:
                while not tensor_cache.audio_outputs.empty():
                    try:
                        tensor = await asyncio.wait_for(
                            tensor_cache.audio_outputs.get_nowait(),
                            timeout=1.0
                        )
                        if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                            tensor.cpu()
                    except asyncio.TimeoutError:
                        logger.warning("Timeout while clearing audio outputs queue")
                        break
                    except asyncio.QueueEmpty:
                        break
                    except Exception as e:
                        logger.error(f"Error clearing audio outputs queue: {e}")
            except Exception as e:
                logger.error(f"Error during audio outputs queue cleanup: {e}")

        except Exception as e:
            logger.error(f"Error cleaning up queues: {str(e)}")
            raise

    async def flush_output_queues(self):
        """Flush all output queues, moving tensors to CPU if needed."""
        try:
            # Clear image outputs queue
            while not tensor_cache.image_outputs.empty():
                try:
                    tensor = await tensor_cache.image_outputs.get()
                    if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                        tensor.cpu()
                except asyncio.TimeoutError:
                    logger.warning("Timeout while flushing image outputs queue")
                    break
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    logger.error(f"Error flushing image outputs queue: {e}")

            # Clear audio outputs queue 
            while not tensor_cache.audio_outputs.empty():
                try:
                    tensor = await tensor_cache.audio_outputs.get()
                    if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                        tensor.cpu()
                except asyncio.TimeoutError:
                    logger.warning("Timeout while flushing audio outputs queue")
                    break
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    logger.error(f"Error flushing audio outputs queue: {e}")

        except Exception as e:
            logger.error(f"Error flushing output queues: {str(e)}")
            raise

    async def cleanup_queues(self):
        """Clean up all queues by removing and freeing any remaining tensors."""
        try:
            # Clear input queues
            while not tensor_cache.image_inputs.empty():
                try:
                    tensor = tensor_cache.image_inputs.get_nowait()
                    if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                        tensor.cpu()
                except Exception as e:
                    logger.error(f"Error clearing image inputs queue: {e}")

            while not tensor_cache.audio_inputs.empty():
                try:
                    tensor = tensor_cache.audio_inputs.get_nowait()
                    if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                        tensor.cpu()
                except Exception as e:
                    logger.error(f"Error clearing audio inputs queue: {e}")

            # Clear output queues
            await self.flush_output_queues()

        except Exception as e:
            logger.error(f"Error cleaning up queues: {str(e)}")
            raise

    def put_video_input(self, frame):
        if self.cleanup_lock.locked():
            logger.warning("Cannot put video input - client is shutting down")
            return
        if tensor_cache.image_inputs.full():
            tensor_cache.image_inputs.get(block=True)
        tensor_cache.image_inputs.put(frame)
    
    def put_audio_input(self, frame):
        if self.cleanup_lock.locked():
            logger.warning("Cannot put audio input - client is shutting down")
            return
        tensor_cache.audio_inputs.put(frame)

    async def get_video_output(self):
        return await tensor_cache.image_outputs.get()
    
    async def get_audio_output(self):
        return await tensor_cache.audio_outputs.get()

    async def get_available_nodes(self):
        """Get metadata and available nodes info in a single pass"""
        # TODO: make it for for multiple prompts
        if not self.running_prompts:
            return {}

        try:
            from comfy.nodes.package import import_all_nodes_in_workspace
            nodes = import_all_nodes_in_workspace()

            all_prompts_nodes_info = {}
            
            for prompt_index, prompt in enumerate(self.current_prompts):
                # Get set of class types we need metadata for, excluding LoadTensor and SaveTensor
                needed_class_types = {
                    node.get('class_type') 
                    for node in prompt.values()
                }
                remaining_nodes = {
                    node_id 
                    for node_id, node in prompt.items() 
                }
                nodes_info = {}

                # Only process nodes until we've found all the ones we need
                for class_type, node_class in nodes.NODE_CLASS_MAPPINGS.items():
                    if not remaining_nodes:  # Exit early if we've found all needed nodes
                        break

                    if class_type not in needed_class_types:
                        continue

                    # Get metadata for this node type (same as original get_node_metadata)
                    input_data = node_class.INPUT_TYPES() if hasattr(node_class, 'INPUT_TYPES') else {}
                    input_info = {}

                    # Process required inputs
                    if 'required' in input_data:
                        for name, value in input_data['required'].items():
                            if isinstance(value, tuple):
                                if len(value) == 1 and isinstance(value[0], list):
                                    # Handle combo box case where value is ([option1, option2, ...],)
                                    input_info[name] = {
                                        'type': 'combo',
                                        'value': value[0],  # The list of options becomes the value
                                    }
                                elif len(value) == 2:
                                    input_type, config = value
                                    input_info[name] = {
                                        'type': input_type,
                                        'required': True,
                                        'min': config.get('min', None),
                                        'max': config.get('max', None),
                                        'widget': config.get('widget', None)
                                    }
                                elif len(value) == 1:
                                    # Handle simple type case like ('IMAGE',)
                                    input_info[name] = {
                                        'type': value[0]
                                    }
                            else:
                                logger.error(f"Unexpected structure for required input {name}: {value}")

                    # Process optional inputs with same logic
                    if 'optional' in input_data:
                        for name, value in input_data['optional'].items():
                            if isinstance(value, tuple):
                                if len(value) == 1 and isinstance(value[0], list):
                                    # Handle combo box case where value is ([option1, option2, ...],)
                                    input_info[name] = {
                                        'type': 'combo',
                                        'value': value[0],  # The list of options becomes the value
                                    }
                                elif len(value) == 2:
                                    input_type, config = value
                                    input_info[name] = {
                                        'type': input_type,
                                        'required': False,
                                        'min': config.get('min', None),
                                        'max': config.get('max', None),
                                        'widget': config.get('widget', None)
                                    }
                                elif len(value) == 1:
                                    # Handle simple type case like ('IMAGE',)
                                    input_info[name] = {
                                        'type': value[0]
                                    }
                            else:
                                logger.error(f"Unexpected structure for optional input {name}: {value}")

                    # Now process any nodes in our prompt that use this class_type
                    for node_id in list(remaining_nodes):
                        node = prompt[node_id]
                        if node.get('class_type') != class_type:
                            continue

                        node_info = {
                            'class_type': class_type,
                            'inputs': {}
                        }

                        if 'inputs' in node:
                            for input_name, input_value in node['inputs'].items():
                                input_metadata = input_info.get(input_name, {})
                                node_info['inputs'][input_name] = {
                                    'value': input_value,
                                    'type': input_metadata.get('type', 'unknown'),
                                    'min': input_metadata.get('min', None),
                                    'max': input_metadata.get('max', None),
                                    'widget': input_metadata.get('widget', None)
                                }
                                # For combo type inputs, include the list of options
                                if input_metadata.get('type') == 'combo':
                                    node_info['inputs'][input_name]['value'] = input_metadata.get('value', [])

                        nodes_info[node_id] = node_info
                        remaining_nodes.remove(node_id)

                    all_prompts_nodes_info[prompt_index] = nodes_info

            return all_prompts_nodes_info

        except Exception as e:
            logger.error(f"Error getting node info: {str(e)}")
            return {}

    async def unload_all_models(self):
        """Unload all models from memory and release CUDA resources.
        
        This sends a special prompt to ComfyUI that triggers unloading of all models.
        This is useful for freeing up GPU memory and ensuring clean state.
        """
        
        logger.info("Unloading all models...")
        try:
            model_management.unload_all_models()
            model_management.soft_empty_cache(True)
        except Exception as e:
            logger.error(f"Error unloading models: {e}")
            raise
        
        logger.info("Clearing Cache...")
        try:
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        except:
            logger.error("Unable to clear cache")
        
        logger.info("Clearing CUDA cache...")
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Models unloaded and CUDA cache cleared")
        except Exception as e:
            logger.error(f"Error unloading models: {e}")
            raise
        
        logger.info("All models unloaded successfully")
