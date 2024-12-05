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
        print("[ComfyStreamClient] Queueing prompt with input shape:", input.shape)
        print("[ComfyStreamClient] Current prompt structure:", self.prompt)
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
        async with self._lock:
            if self.prompt:
                nodes_info = {}
                print("[ComfyStreamClient] Getting node metadata...")
                node_metadata = await self.get_node_metadata()
                print(f"[ComfyStreamClient] Retrieved metadata: {json.dumps(node_metadata, indent=2)}")
                
                for node_id, node in self.prompt.items():
                    class_type = node.get('class_type')
                    print(f"[ComfyStreamClient] Processing node {node_id} of type {class_type}")
                    node_info = {
                        'class_type': class_type,
                        'inputs': {}
                    }
                    
                    if 'inputs' in node:
                        node_info['inputs'] = {}
                        for input_name, input_value in node['inputs'].items():
                            print(f"[ComfyStreamClient] Processing input {input_name} for node {node_id}")
                            input_info = {
                                'value': input_value,
                                'type': 'unknown'
                            }
                            
                            if class_type in node_metadata:
                                print(f"[ComfyStreamClient] Found metadata for {class_type}")
                                input_meta = node_metadata[class_type]['input'].get(input_name, {})
                                print(f"[ComfyStreamClient] Input metadata for {input_name}: {input_meta}")
                                input_info.update({
                                    'type': input_meta.get('type', 'unknown'),
                                    'min': input_meta.get('min', None),
                                    'max': input_meta.get('max', None),
                                    'widget': input_meta.get('widget', None)
                                })
                            else:
                                print(f"[ComfyStreamClient] No metadata found for {class_type}")
                                
                            print(f"[ComfyStreamClient] Final input info for {input_name}: {input_info}")
                            node_info['inputs'][input_name] = input_info
                    
                    nodes_info[node_id] = node_info
                
                print(f"[ComfyStreamClient] Final nodes info: {json.dumps(nodes_info, indent=2)}")
                return nodes_info
            return {}

    async def get_node_metadata(self):
        """Get metadata about node types from ComfyUI"""
        try:
            # ComfyUI exposes node information through the API
            object_info = await self.comfy_client.get_object_info()
            return object_info
        except Exception as e:
            print(f"[ComfyStreamClient] Error getting node metadata: {str(e)}")
            return {}
