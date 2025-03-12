"""ComfyStream Web UI nodes"""

import os
import folder_paths


# Define a simple Python class for the UI Preview node
class ComfyStreamUIPreview:
    """
    This is a dummy Python class that corresponds to the JavaScript node.
    It's needed for ComfyUI to properly register and execute the node.
    The actual implementation is in the JavaScript file.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}, "optional": {}}

    RETURN_TYPES = ()

    FUNCTION = "execute"
    CATEGORY = "ComfyStream"

    def execute(self):
        # This function doesn't do anything as the real work is done in JavaScript
        # But we need to return something to satisfy the ComfyUI node execution system
        return ("UI Preview Node Executed",)


# Register the node class
NODE_CLASS_MAPPINGS = {"ComfyStreamUIPreview": ComfyStreamUIPreview}

# Display names for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {"ComfyStreamUIPreview": "ComfyStream UI Preview"}
