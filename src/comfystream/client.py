import torch
import asyncio

from comfy.api.components.schema.prompt import PromptDictInput
from comfy.cli_args_types import Configuration
from comfy.client.embedded_comfy_client import EmbeddedComfyClient
from comfystream import tensor_cache
from comfystream.utils import convert_prompt


class ComfyStreamClient:
    def __init__(self, **kwargs):
        config = Configuration(**kwargs)
        # TODO: Need to handle cleanup for EmbeddedComfyClient if not using async context manager?
        self.comfy_client = EmbeddedComfyClient(config)
        self.prompt = None

    def set_prompt(self, prompt: PromptDictInput):
        self.prompt = convert_prompt(prompt)

    async def queue_prompt(self, input: torch.Tensor) -> torch.Tensor:
        tensor_cache.inputs.append(input)

        output_fut = asyncio.Future()
        tensor_cache.outputs.append(output_fut)

        await self.comfy_client.queue_prompt(self.prompt)

        return await output_fut
