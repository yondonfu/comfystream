import av
import torch
import numpy as np
import asyncio

from typing import Any, Dict, Union, List
from comfystream.client import ComfyStreamClient

WARMUP_RUNS = 10


class Pipeline:
    def __init__(self, **kwargs):
        self.client = ComfyStreamClient(**kwargs, max_workers=5) # TODO: hardcoded max workers, should it be configurable?

        self.video_futures = asyncio.Queue()
        self.audio_futures = asyncio.Queue()

    async def warm_video(self):
        dummy_video_inp = torch.randn(1, 512, 512, 3)

        for _ in range(WARMUP_RUNS):
            image_out_fut = self.client.put_video_input(dummy_video_inp)
            await image_out_fut

    async def warm_audio(self):
        dummy_audio_inp = np.random.randint(-32768, 32767, 48 * 20, dtype=np.int16)  # TODO: might affect the workflow, due to buffering

        futs = []
        for _ in range(WARMUP_RUNS):
            audio_out_fut = self.client.put_audio_input(dummy_audio_inp)
            futs.append(audio_out_fut)

        await asyncio.gather(*futs)

    async def set_prompts(self, prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]]):
        if isinstance(prompts, dict):
            await self.client.set_prompts([prompts])
        else:
            await self.client.set_prompts(prompts)

    async def put_video_frame(self, frame: av.VideoFrame):
        inp_tensor = self.video_preprocess(frame)
        out_future = self.client.put_video_input(inp_tensor)
        await self.video_futures.put((out_future, frame.pts, frame.time_base))

    async def put_audio_frame(self, frame: av.AudioFrame):
        inp_tensor = self.audio_preprocess(frame)
        out_future = self.client.put_audio_input(inp_tensor)
        await self.audio_futures.put((out_future, frame.pts, frame.time_base, frame.sample_rate))

    def video_preprocess(self, frame: av.VideoFrame) -> torch.Tensor:
        frame_np = frame.to_ndarray(format="rgb24").astype(np.float32) / 255.0
        return torch.from_numpy(frame_np).unsqueeze(0)
    
    def audio_preprocess(self, frame: av.AudioFrame) -> torch.Tensor:
        return frame.to_ndarray().ravel().reshape(-1, 2).mean(axis=1).astype(np.int16)
    
    def video_postprocess(self, output: torch.Tensor) -> av.VideoFrame:
        return av.VideoFrame.from_ndarray(
            (output * 255.0).clamp(0, 255).to(dtype=torch.uint8).squeeze(0).cpu().numpy()
        )

    def audio_postprocess(self, output: torch.Tensor) -> av.AudioFrame:
        return av.AudioFrame.from_ndarray(output.reshape(1, -1), layout="mono")
    
    async def get_processed_video_frame(self):
        out_fut, pts, time_base = await self.video_futures.get()
        frame = self.video_postprocess(await out_fut)
        frame.pts = pts
        frame.time_base = time_base
        return frame

    async def get_processed_audio_frame(self):
        out_fut, pts, time_base, sample_rate = await self.audio_futures.get()
        frame = self.audio_postprocess(await out_fut)
        frame.pts = pts
        frame.time_base = time_base
        frame.sample_rate = sample_rate
        return frame
    
    async def get_nodes_info(self) -> Dict[str, Any]:
        """Get information about all nodes in the current prompt including metadata."""
        nodes_info = await self.client.get_available_nodes()
        return nodes_info