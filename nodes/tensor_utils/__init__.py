"""Tensor utility nodes for ComfyStream"""

from .load_tensor import LoadTensor
from .save_tensor import SaveTensor

NODE_CLASS_MAPPINGS = {"LoadTensor": LoadTensor, "SaveTensor": SaveTensor}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS"]
