import torch
import queue
from comfystream import tensor_cache
from comfystream.exceptions import ComfyStreamInputTimeoutError


class LoadTensor:
    CATEGORY = "ComfyStream/Loaders"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute"
    DESCRIPTION = "Load image tensor from ComfyStream input with timeout."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "timeout_seconds": ("FLOAT", {
                    "default": 1.0, 
                    "min": 0.1, 
                    "max": 30.0,
                    "step": 0.1,
                    "tooltip": "Timeout in seconds"
                }),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def execute(self, timeout_seconds: float = 1.0):
        try:
            frame = tensor_cache.image_inputs.get(block=True, timeout=timeout_seconds)
            frame.side_data.skipped = False
            return (frame.side_data.input,)
        except queue.Empty:
            raise ComfyStreamInputTimeoutError("video", timeout_seconds)
