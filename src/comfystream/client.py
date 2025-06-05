import asyncio
from typing import List
import logging
import torch

from comfystream import tensor_cache
from comfystream.utils import convert_prompt

from comfy.api.components.schema.prompt import PromptDictInput
from comfy.cli_args_types import Configuration
from comfy.client.embedded_comfy_client import EmbeddedComfyClient

logger = logging.getLogger(__name__)


class ComfyStreamClient:
    def __init__(self, max_workers: int = 1, **kwargs):
        config = Configuration(**kwargs)
        self.comfy_client = EmbeddedComfyClient(config, max_workers=max_workers)
        self.running_prompts = {} # To be used for cancelling tasks
        self.current_prompts = []
        self.cleanup_lock = asyncio.Lock()
        self.is_shutting_down = False

    async def set_prompts(self, prompts: List[PromptDictInput]):
        await self.cancel_running_prompts()
        self.current_prompts = [convert_prompt(prompt) for prompt in prompts]
        for idx in range(len(self.current_prompts)):
            task = asyncio.create_task(self.run_prompt(idx))
            self.running_prompts[idx] = task

    async def update_prompts(self, prompts: List[PromptDictInput]):
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
            try:
                await self.comfy_client.queue_prompt(self.current_prompts[prompt_index])
            except asyncio.CancelledError:
                raise
            except Exception as e:
                await self.cleanup()
                logger.error(f"Error running prompt: {str(e)}")
                raise

    async def cleanup(self, exit_client: bool = False):
        """Clean up all resources and stop all tasks."""
        async with self.cleanup_lock:
            try:
                # Set shutdown flag first to prevent new operations
                self.is_shutting_down = True
                logger.info("Starting client cleanup")

                # First cancel all running prompts
                await self.cancel_running_prompts()
                
                # Then clean up queues
                await self.cleanup_queues()
                
                # Finally unload all models to free GPU memory
                await self.unload_all_models()
                
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
                            logger.warning("Timeout while disposing comfy_client")
                        except Exception as e:
                            logger.error(f"Error disposing comfy_client: {e}")

                logger.info("Client cleanup complete")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                raise
            finally:
                # Reset the shutdown flag only if we're not shutting down
                if not self.is_shutting_down:
                    self.is_shutting_down = False

    async def cancel_running_prompts(self):
        """Cancel all running prompt tasks."""
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

    def put_video_input(self, frame):
        if self.is_shutting_down:
            logger.warning("Cannot put video input - client is shutting down")
            return
        if tensor_cache.image_inputs.full():
            tensor_cache.image_inputs.get(block=True)
        tensor_cache.image_inputs.put(frame)
    
    def put_audio_input(self, frame):
        if self.is_shutting_down:
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
        try:
            unload_prompt = {
                "2": {
                    "inputs": {
                        "value": [
                            "12",
                            0
                        ]
                    },
                    "class_type": "UnloadAllModels",
                    "_meta": {
                        "title": "UnloadAllModels"
                    }
                },
                "4": {
                    "inputs": {
                        "width": 512,
                        "height": 512,
                        "font_size": 48,
                        "font_color": "white",
                        "background_color": "black",
                        "x_offset": 0,
                        "y_offset": 0,
                        "align": "center",
                        "wrap_width": 0,
                        "any": [
                            "2",
                            0
                        ]
                    },
                    "class_type": "TextRenderer",
                    "_meta": {
                        "title": "Text Renderer"
                    }
                },
                "6": {
                    "inputs": {
                        "images": [
                            "4",
                            0
                        ]
                    },
                    "class_type": "PreviewImage",
                    "_meta": {
                        "title": "Preview Image"
                    }
                },
                "8": {
                    "inputs": {
                        "image": "example-512x512.png"
                    },
                    "class_type": "LoadImage",
                    "_meta": {
                        "title": "Load Image"
                    }
                },
                "12": {
                    "inputs": {
                        "text": "true",
                        "strip_whitespace": True,
                        "remove_empty_lines": False
                    },
                    "class_type": "MultilineText",
                    "_meta": {
                        "title": "Multiline Text"
                    }
                }
            }
            
            # Convert the prompt to the format expected by ComfyUI
            converted_prompt = convert_prompt(unload_prompt)
            
            # Queue the unload prompt
            await self.comfy_client.queue_prompt(converted_prompt)
            
            # Wait a bit to ensure the unload completes
            await asyncio.sleep(1.0)
            
            # Clear CUDA cache after models are unloaded
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Models unloaded and CUDA cache cleared")
                
        except Exception as e:
            logger.error(f"Error unloading models: {e}")
            raise
