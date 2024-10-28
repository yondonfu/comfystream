import torch
import asyncio
import json

from comfystream.client import ComfyStreamClient


async def main():
    cwd = "/home/user/comfy-hiddenswitch"
    client = ComfyStreamClient(cwd=cwd)

    with open("./examples/tensor-utils-example-workflow.json", "r") as f:
        prompt = json.load(f)

    client.set_prompt(prompt)

    input = torch.randn(1, 512, 512, 3)
    output = await client.queue_prompt(input)
    print(output.shape)


if __name__ == "__main__":
    asyncio.run(main())
