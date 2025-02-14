import os
import pathlib
import subprocess
import shutil

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

# Get the path to the UI directory
UI_DIR = pathlib.Path(__file__).parent / "ui"

def get_npm_command():
    """Get the npm command for the current platform"""
    npm_cmd = shutil.which("npm")
    if npm_cmd is None:
        raise RuntimeError("npm not found in PATH. Please install Node.js and npm.")
    return npm_cmd

def run_npm_command(command, cwd):
    """Run an npm command in a platform-agnostic way"""
    npm_cmd = get_npm_command()
    full_cmd = [npm_cmd] + command.split()
    
    try:
        return subprocess.run(
            full_cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running npm command: {e.stderr}")
        raise

def ensure_ui_ready():
    """Ensure the UI is ready (dependencies installed)"""
    try:
        # Check if node_modules exists
        if not (UI_DIR / "node_modules").exists():
            print("[ComfyStream] Installing dependencies...")
            run_npm_command("install", UI_DIR)
            print("[ComfyStream] Dependencies installed successfully")
    except Exception as e:
        print(f"[ComfyStream] Error preparing UI: {str(e)}")
        raise

# Create __init__.py files in ComfyUI directories
ensure_init_files()
# Ensure UI is ready on module load
ensure_ui_ready()

WEB_DIRECTORY = "./nodes/web/js"
# Import and expose node classes
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS'] 