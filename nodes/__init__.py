"""ComfyStream nodes package"""

from .tensor_utils import *
from .video_stream_utils import *
from .launcher import *

# Collect all NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS from submodules
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Import and update mappings from submodules
for module in [tensor_utils, video_stream_utils, launcher]:
    if hasattr(module, 'NODE_CLASS_MAPPINGS'):
        NODE_CLASS_MAPPINGS.update(module.NODE_CLASS_MAPPINGS)
    if hasattr(module, 'NODE_DISPLAY_NAME_MAPPINGS'):
        NODE_DISPLAY_NAME_MAPPINGS.update(module.NODE_DISPLAY_NAME_MAPPINGS)

# Web directory for UI components
import os
WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")

NODE_DISPLAY_NAME_MAPPINGS["ComfyStreamLauncher"] = "Launch ComfyStream 🚀"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']