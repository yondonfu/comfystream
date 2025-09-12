"""Tensor utility nodes for ComfyStream"""

from .load_tensor import LoadTensor
from .save_tensor import SaveTensor
from .save_text_tensor import SaveTextTensor

NODE_CLASS_MAPPINGS = {
    "LoadTensor": LoadTensor,
    "SaveTensor": SaveTensor,
    "SaveTextTensor": SaveTextTensor,
}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS"]
