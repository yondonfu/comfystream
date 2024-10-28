from .load_tensor import LoadTensor
from .save_tensor import SaveTensor

NODE_CLASS_MAPPINGS = {"LoadTensor": LoadTensor, "SaveTensor": SaveTensor}

__all__ = ["NODE_CLASS_MAPPINGS"]
