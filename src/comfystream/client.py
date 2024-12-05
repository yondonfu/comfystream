import torch
import asyncio
from typing import Any
import json

from comfy.api.components.schema.prompt import PromptDictInput
from comfy.cli_args_types import Configuration
from comfy.client.embedded_comfy_client import EmbeddedComfyClient
from comfystream import tensor_cache
from comfystream.utils import convert_prompt


class ComfyStreamClient:
    def __init__(self, **kwargs):
        print("[ComfyStreamClient] Initializing with kwargs:", kwargs)
        config = Configuration(**kwargs)
        self.comfy_client = EmbeddedComfyClient(config)
        self.prompt = None
        self._lock = asyncio.Lock()

    def set_prompt(self, prompt: PromptDictInput):
        print("[ComfyStreamClient] Setting prompt:", prompt)
        self.prompt = convert_prompt(prompt)
        print("[ComfyStreamClient] Converted prompt:", self.prompt)
        print("[ComfyStreamClient] Prompt type:", type(self.prompt))
        for node_id, node in self.prompt.items():
            print(f"[ComfyStreamClient] Node {node_id} type: {type(node)}")
            if hasattr(node, 'keys'):
                print(f"[ComfyStreamClient] Node {node_id} keys: {list(node.keys())}")
                if 'inputs' in node:
                    print(f"[ComfyStreamClient] Node {node_id} inputs type: {type(node['inputs'])}")

    async def update_node_input(self, node_id: str, field_name: str, value: Any):
        print(f"[ComfyStreamClient] Attempting to update node {node_id}, field {field_name} to {value}")
        print(f"[ComfyStreamClient] Current prompt type: {type(self.prompt)}")
        print(f"[ComfyStreamClient] Current prompt: {self.prompt}")
        
        async with self._lock:
            if self.prompt and node_id in self.prompt:
                # Create a completely new mutable dictionary structure
                prompt_dict = {}
                for key, node in self.prompt.items():
                    node_dict = dict(node)
                    if 'inputs' in node_dict:
                        node_dict['inputs'] = dict(node_dict['inputs'])
                    prompt_dict[key] = node_dict
                
                # Update the specific node's input
                if 'inputs' not in prompt_dict[node_id]:
                    prompt_dict[node_id]['inputs'] = {}
                    
                try:
                    value = float(value)
                except ValueError:
                    pass
                    
                prompt_dict[node_id]['inputs'][field_name] = value
                
                # Convert back to PromptDict type
                from comfy.api.components.schema.prompt import Prompt
                self.prompt = Prompt.validate(prompt_dict)
                
                print(f"[Client] Updated node {node_id}, field {field_name} to value {value}")
                print(f"[Client] New prompt structure: {self.prompt}")

    async def queue_prompt(self, input: torch.Tensor) -> torch.Tensor:
        async with self._lock:
            tensor_cache.inputs.append(input)
            output_fut = asyncio.Future()
            tensor_cache.outputs.append(output_fut)
            try:
                await self.comfy_client.queue_prompt(self.prompt)
            except Exception as e:
                print(f"[ComfyStreamClient] Error queueing prompt: {str(e)}")
                print(f"[ComfyStreamClient] Error type: {type(e)}")
                raise
            return await output_fut

    async def get_available_nodes(self):
        """Get metadata and available nodes info in a single pass"""
        async with self._lock:
            if not self.prompt:
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
                                print(f"[ComfyStreamClient] Unexpected structure for required input {name}: {value}")
                    
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
                                print(f"[ComfyStreamClient] Unexpected structure for optional input {name}: {value}")
                    
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
                print(f"[ComfyStreamClient] Error getting node info: {str(e)}")
                return {}



    # async def get_available_nodes(self):
    #     async with self._lock:
    #         if self.prompt:
    #             nodes_info = {}
    #             node_metadata = await self.get_node_metadata()
    #             for node_id, node in self.prompt.items():
    #                 class_type = node.get('class_type')
    #                 node_info = {
    #                     'class_type': class_type,
    #                     'inputs': {}
    #                 }
                    
    #                 if 'inputs' in node:
    #                     node_info['inputs'] = {}
    #                     for input_name, input_value in node['inputs'].items():
    #                         input_info = {
    #                             'value': input_value,
    #                             'type': 'unknown'
    #                         }
                            
    #                         if class_type in node_metadata:
    #                             input_meta = node_metadata[class_type]['input'].get(input_name, {})
    #                             input_info.update({
    #                                 'type': input_meta.get('type', 'unknown'),
    #                                 'min': input_meta.get('min', None),
    #                                 'max': input_meta.get('max', None),
    #                                 'widget': input_meta.get('widget', None)
    #                             })
    #                         else:
    #                             print(f"[ComfyStreamClient] No metadata found for {class_type}")
                                
    #                         node_info['inputs'][input_name] = input_info
                    
    #                 nodes_info[node_id] = node_info
                
    #             return nodes_info
    #         return {}

    # async def get_node_metadata(self):
    #     """Get metadata about node types from ComfyUI"""
    #     try:
    #         # Access the node mappings directly from the ComfyUI nodes module
    #         from comfy.nodes.package import import_all_nodes_in_workspace
    #         nodes = import_all_nodes_in_workspace()
            
    #         node_info = {}
    #         for class_type, node_class in nodes.NODE_CLASS_MAPPINGS.items():
    #             input_data = node_class.INPUT_TYPES() if hasattr(node_class, 'INPUT_TYPES') else {}
                
    #             # Extract input metadata including types, min/max values, and widgets
    #             input_info = {}
    #             if 'required' in input_data:
    #                 for name, value in input_data['required'].items():
    #                     if isinstance(value, tuple) and len(value) == 2:
    #                         input_type, config = value
    #                         input_info[name] = {
    #                             'type': input_type,
    #                             'required': True,
    #                             'min': config.get('min', None),
    #                             'max': config.get('max', None),
    #                             'widget': config.get('widget', None)
    #                         }
    #                     else:
    #                         print(f"[ComfyStreamClient] Unexpected structure for required input {name}: {value}")
                
    #             if 'optional' in input_data:
    #                 for name, value in input_data['optional'].items():
    #                     if isinstance(value, tuple) and len(value) == 2:
    #                         input_type, config = value
    #                         input_info[name] = {
    #                             'type': input_type,
    #                             'required': False,
    #                             'min': config.get('min', None),
    #                             'max': config.get('max', None),
    #                             'widget': config.get('widget', None)
    #                         }
    #                     else:
    #                         print(f"[ComfyStreamClient] Unexpected structure for optional input {name}: {value}")

    #             node_info[class_type] = {
    #                 'input': input_info,
    #                 'output': node_class.RETURN_TYPES if hasattr(node_class, 'RETURN_TYPES') else [],
    #                 'output_is_list': node_class.OUTPUT_IS_LIST if hasattr(node_class, 'OUTPUT_IS_LIST') else [],
    #                 'output_node': getattr(node_class, 'OUTPUT_NODE', False)
    #             }
                
    #         return node_info
    #     except Exception as e:
    #         print(f"[ComfyStreamClient] Error getting node metadata: {str(e)}")
    #         return {}
