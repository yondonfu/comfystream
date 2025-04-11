import asyncio
from typing import List
import logging

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

    async def set_prompts(self, prompts: List[PromptDictInput]):
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
        self.current_prompts = [convert_prompt(prompt) for prompt in prompts]

    async def run_prompt(self, prompt_index: int):
        while True:
            try:
                await self.comfy_client.queue_prompt(self.current_prompts[prompt_index])
            except Exception as e:
                await self.cleanup()
                logger.error(f"Error running prompt: {str(e)}")
                raise

    async def cleanup(self):
        async with self.cleanup_lock:
            for task in self.running_prompts.values():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self.running_prompts.clear()

            if self.comfy_client.is_running:
                await self.comfy_client.__aexit__()

            await self.cleanup_queues()
            logger.info("Client cleanup complete")

        
    async def cleanup_queues(self):
        while not tensor_cache.image_inputs.empty():
            tensor_cache.image_inputs.get()

        while not tensor_cache.audio_inputs.empty():
            tensor_cache.audio_inputs.get()

        while not tensor_cache.image_outputs.empty():
            await tensor_cache.image_outputs.get()

        while not tensor_cache.audio_outputs.empty():
            await tensor_cache.audio_outputs.get()

    def put_video_input(self, frame):
        if tensor_cache.image_inputs.full():
            tensor_cache.image_inputs.get(block=True)
        tensor_cache.image_inputs.put(frame)
    
    def put_audio_input(self, frame):
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
                            if isinstance(value, tuple) and len(value) == 2:
                                input_type, config = value
                                input_info[name] = {
                                    'type': input_type,
                                    'required': True,
                                    'min': config.get('min', None),
                                    'max': config.get('max', None),
                                    'widget': config.get('widget', None)
                                }
                            else:
                                logger.error(f"Unexpected structure for required input {name}: {value}")
                    
                    # Process optional inputs
                    if 'optional' in input_data:
                        for name, value in input_data['optional'].items():
                            if isinstance(value, tuple) and len(value) == 2:
                                input_type, config = value
                                input_info[name] = {
                                    'type': input_type,
                                    'required': False,
                                    'min': config.get('min', None),
                                    'max': config.get('max', None),
                                    'widget': config.get('widget', None)
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
                                node_info['inputs'][input_name] = {
                                    'value': input_value,
                                    'type': input_info.get(input_name, {}).get('type', 'unknown'),
                                    'min': input_info.get(input_name, {}).get('min', None),
                                    'max': input_info.get(input_name, {}).get('max', None),
                                    'widget': input_info.get(input_name, {}).get('widget', None)
                                }
                        
                        nodes_info[node_id] = node_info
                        remaining_nodes.remove(node_id)

                    all_prompts_nodes_info[prompt_index] = nodes_info
            
            return all_prompts_nodes_info
            
        except Exception as e:
            logger.error(f"Error getting node info: {str(e)}")
            return {}
