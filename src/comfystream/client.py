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
                if "inputs" not in self.prompt[node_id]:
                    self.prompt[node_id]["inputs"] = {}
                self.prompt[node_id]["inputs"][field_name] = value

    async def queue_prompt(self, input: torch.Tensor) -> torch.Tensor:
        async with self._lock:
            tensor_cache.inputs.append(input)
            output_fut = asyncio.Future()
            tensor_cache.outputs.append(output_fut)
            await self.comfy_client.queue_prompt(self.prompt)
            return await output_fut
