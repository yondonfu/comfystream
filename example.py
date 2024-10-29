import torch
import asyncio
import json

from comfystream.client import ComfyStreamClient


async def main():
    # Configuration options:
    # https://github.com/hiddenswitch/ComfyUI/blob/89d07f3adf32a6703181343bc732bd85104bb653/comfy/cli_args_types.py#L37
    cwd = "/home/user/comfy-hiddenswitch"
    client = ComfyStreamClient(cwd=cwd)

    with open("./workflows/tensor-utils-example-workflow.json", "r") as f:
        prompt = json.load(f)

    client.set_prompt(prompt)

    # Comfy will cache nodes that only need to be run once (i.e. a node that loads model weights)
    # We can run the prompt once before actual inputs come in to "warmup"
    input = torch.randn(1, 512, 512, 3)
    await client.queue_prompt(input)

    # Now we are ready to process actual inputs
    # We can pass an image tensor directly
    input = torch.randn(1, 512, 512, 3)
    output = await client.queue_prompt(input)
    print(output.shape)


if __name__ == "__main__":
    asyncio.run(main())
