import torch

from comfystream import tensor_cache


class SaveTensor:
    CATEGORY = "tensor_utils"
    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
            }
        }

    @classmethod
    def IS_CHANGED(s):
        return float("nan")

    def execute(self, images: torch.Tensor):
        fut = tensor_cache.outputs.pop()
        fut.set_result(images)
        return images
