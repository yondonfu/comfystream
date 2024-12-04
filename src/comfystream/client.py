import torch
import asyncio
from typing import Any

from comfy.api.components.schema.prompt import PromptDictInput
from comfy.cli_args_types import Configuration
from comfy.client.embedded_comfy_client import EmbeddedComfyClient
from comfystream import tensor_cache
from comfystream.utils import convert_prompt


class ComfyStreamClient:
    def __init__(self, **kwargs):
        config = Configuration(**kwargs)
        self.comfy_client = EmbeddedComfyClient(config)
        self.prompt = None
        self._lock = asyncio.Lock()

    def set_prompt(self, prompt: PromptDictInput):
        self.prompt = convert_prompt(prompt)

    async def update_node_input(self, node_id: str, field_name: str, value: Any):
        """Update a specific input field of a node in the prompt"""
        async with self._lock:
            if self.prompt and node_id in self.prompt:
                # Convert the prompt to a mutable dictionary if it isn't already
                prompt_dict = dict(self.prompt)
                node_dict = dict(prompt_dict[node_id])
                
                if "inputs" not in node_dict:
                    node_dict["inputs"] = {}
                else:
                    node_dict["inputs"] = dict(node_dict["inputs"])
                    
                # Convert value to the appropriate type (assuming numeric value)
                try:
                    value = float(value)  # or int(value) if you need integers
                except ValueError:
                    pass  # Keep as string if not numeric
                    
                node_dict["inputs"][field_name] = value
                prompt_dict[node_id] = node_dict
                self.prompt = prompt_dict
                
                # Debug logging
                print(f"[Client] Updated node {node_id}, field {field_name} to value {value}")
                print(f"[Client] New prompt structure: {self.prompt}")

    async def queue_prompt(self, input: torch.Tensor) -> torch.Tensor:
        async with self._lock:
            tensor_cache.inputs.append(input)
            output_fut = asyncio.Future()
            tensor_cache.outputs.append(output_fut)
            await self.comfy_client.queue_prompt(self.prompt)
            return await output_fut
