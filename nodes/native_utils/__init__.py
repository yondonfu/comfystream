from .load_image_base64 import LoadImageBase64
from .send_image_websocket import SendImageWebsocket

# This dictionary is used by ComfyUI to register the nodes
NODE_CLASS_MAPPINGS = {
    "LoadImageBase64": LoadImageBase64, 
    "SendImageWebsocket": SendImageWebsocket
}

# This dictionary provides display names for the nodes in the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageBase64": "Load Image Base64 (ComfyStream)",
    "SendImageWebsocket": "Send Image Websocket (ComfyStream)"
}

# Export these variables for ComfyUI to use
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
