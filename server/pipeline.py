import torch
import av
import numpy as np

from typing import Any, Dict
from comfystream.client import ComfyStreamClient


class Pipeline:
    def __init__(self, prompt: Dict[Any, Any], **kwargs):
        self.client = ComfyStreamClient(**kwargs)
        self.client.set_prompt(prompt)

    async def update_parameters(self, params: Dict[Any, Any]):
        """Update workflow parameters dynamically
        
        params format:
        {
            "node_id": str,            # ID of the node to update
            "field_name": str,         # Name of the input field
            "value": Any              # New value for the field
        }
        """
        await self.client.update_node_input(
            params["node_id"],
            params["field_name"],
            params["value"]
        )

    async def warm(self):
        frame = torch.randn(1, 512, 512, 3)
        await self.predict(frame)

    def preprocess(self, frame: av.VideoFrame) -> torch.Tensor:
        frame_np = frame.to_ndarray(format="rgb24").astype(np.float32) / 255.0
        return torch.from_numpy(frame_np).unsqueeze(0)

    async def predict(self, frame: torch.Tensor) -> torch.Tensor:
        return await self.client.queue_prompt(frame)

    def postprocess(self, frame: torch.Tensor) -> av.VideoFrame:
        return av.VideoFrame.from_ndarray(
            (frame * 255.0).clamp(0, 255).to(dtype=torch.uint8).squeeze(0).cpu().numpy()
        )

    async def __call__(self, frame: av.VideoFrame) -> av.VideoFrame:
        pre_output = self.preprocess(frame)
        pred_output = await self.predict(pre_output)
        post_output = self.postprocess(pred_output)

        post_output.pts = frame.pts
        post_output.time_base = frame.time_base

        return post_output

    async def get_nodes_info(self) -> Dict[str, Any]:
        """Get information about all nodes in the current prompt including metadata."""
        return await self.client.get_available_nodes()