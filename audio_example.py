import json
import asyncio
import torchaudio

from comfystream.client import ComfyStreamClient

async def main():
    cwd = "/home/user/ComfyUI"
    client = ComfyStreamClient(cwd=cwd)

    with open("./workflows/audio-whsiper-example-workflow.json", "r") as f:
        prompt = json.load(f)

    client.set_prompt(prompt)

    waveform, _ = torchaudio.load("/home/user/harvard.wav")
    if waveform.ndim > 1:
        audio_tensor = waveform.mean(dim=0)

    output = await client.queue_prompt(audio_tensor)
    print(output)

if __name__ == "__main__":
    asyncio.run(main())