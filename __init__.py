import os
import pathlib

def ensure_init_files():
    """Create __init__.py files in comfy/ and comfy_extras/ directories if they don't exist"""
    # Go up two levels from custom_nodes/comfystream_inside to reach ComfyUI root
    comfy_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    base_dirs = ['comfy', 'comfy_extras']
    for base_dir in base_dirs:
        base_path = os.path.join(comfy_root, base_dir)
        if not os.path.exists(base_path):
            continue
            
        # Create __init__.py in the root of base_dir first
        root_init = os.path.join(base_path, "__init__.py")
        if not os.path.exists(root_init):
            with open(root_init, 'w') as f:
                f.write("")
                
        # Then walk subdirectories
        for root, dirs, files in os.walk(base_path):
            init_path = os.path.join(root, "__init__.py")
            if not os.path.exists(init_path):
                with open(init_path, 'w') as f:
                    f.write("")

# Create __init__.py files in ComfyUI directories
ensure_init_files()

# Point to the directory containing our web files
WEB_DIRECTORY = "./nodes/web/js"

# Import and expose node classes
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS'] 