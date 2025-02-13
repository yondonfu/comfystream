"""Launcher node for ComfyStream"""

from .launcher_node import ComfyStreamLauncher

NODE_CLASS_MAPPINGS = {
    "ComfyStreamLauncher": ComfyStreamLauncher
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComfyStreamLauncher": "Launch ComfyStream 🚀"
}

__all__ = ["NODE_CLASS_MAPPINGS"]
