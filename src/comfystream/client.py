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
        # TODO: Need to handle cleanup for EmbeddedComfyClient if not using async context manager?
        self.comfy_client = EmbeddedComfyClient(config, max_workers=max_workers)
        self.running_prompts = []

    async def set_prompts(self, prompts: List[PromptDictInput]):
        await self.cancel_running_tasks()
        for prompt in [convert_prompt(prompt) for prompt in prompts]:
            task = asyncio.create_task(self.run_prompt(prompt))
            self.running_prompts.append({"task": task, "prompt": prompt})

    async def cancel_running_tasks(self):
        while self.running_prompts:
            task = self.running_prompts.pop()
            task["task"].cancel()
            await task["task"]

    async def run_prompt(self, prompt: PromptDictInput):
        while True:
            try:
                await self.comfy_client.queue_prompt(prompt)
            except Exception as e:
                logger.error(f"Error running prompt: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                raise

    def put_video_input(self, inp_tensor):
        out_future = asyncio.Future()
        tensor_cache.image_outputs.put(out_future)
        tensor_cache.image_inputs.put(inp_tensor)
        return out_future
    
    def put_audio_input(self, inp_tensor):
        out_future = asyncio.Future()
        tensor_cache.audio_outputs.put(out_future)
        tensor_cache.audio_inputs.put(inp_tensor)
        return out_future

    async def get_available_nodes(self):
        """Get metadata and available nodes info in a single pass"""
        # TODO: make it for for multiple prompts
        if not self.running_prompts:
            return {}

        try:
            from comfy.nodes.package import import_all_nodes_in_workspace
            nodes = import_all_nodes_in_workspace()
            
            # Get set of class types we need metadata for, excluding LoadTensor and SaveTensor
            needed_class_types = {
                node.get('class_type') 
                for node in self.prompt.values() 
                if node.get('class_type') not in ('LoadTensor', 'SaveTensor')
            }
            remaining_nodes = {
                node_id 
                for node_id, node in self.prompt.items() 
                if node.get('class_type') not in ('LoadTensor', 'SaveTensor')
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
                    node = self.prompt[node_id]
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
            
            return nodes_info
            
        except Exception as e:
            logger.error(f"Error getting node info: {str(e)}")
            return {}
