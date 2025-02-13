"""Video stream utility nodes for ComfyStream"""

from .primary_input_load_image import PrimaryInputLoadImage 

NODE_CLASS_MAPPINGS = {"PrimaryInputLoadImage": PrimaryInputLoadImage}
NODE_DISPLAY_NAME_MAPPINGS = {}

__all__ = ["NODE_CLASS_MAPPINGS"]
