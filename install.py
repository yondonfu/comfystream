import os
import subprocess
import argparse
import logging
import pathlib
import sys
import tarfile
import tempfile
import urllib.request
import toml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_project_version(workspace: str) -> str:
    """Read project version from pyproject.toml"""
    pyproject_path = os.path.join(workspace, "pyproject.toml")
    try:
        with open(pyproject_path, "r") as f:
            pyproject = toml.load(f)
            return pyproject["project"]["version"]
    except Exception as e:
        logger.error(f"Failed to read version from pyproject.toml: {e}")
        return "unknown"
    
def ensure_init_files(workspace: str):
    """Create __init__.py files in comfy/ and comfy_extras/ directories if they don't exist"""
    base_dirs = ['comfy', 'comfy_extras']
    for base_dir in base_dirs:
        base_path = os.path.join(workspace, base_dir)
        if not os.path.exists(base_path):
            continue
            
        # Create __init__.py in the root of base_dir first
        root_init = os.path.join(base_path, "__init__.py")
        if not os.path.exists(root_init):
            logger.info(f"Creating {root_init}")
            with open(root_init, 'w') as f:
                f.write("")
                
        # Then walk subdirectories
        for root, dirs, files in os.walk(base_path):
            init_path = os.path.join(root, "__init__.py")
            if not os.path.exists(init_path):
                logger.info(f"Creating {init_path}")
                with open(init_path, 'w') as f:
                    f.write("")


def download_and_extract_ui_files(version: str):
    """Download and extract UI files to the workspace"""

    output_dir = os.path.join(os.getcwd(), "nodes", "web")
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    base_url = urllib.parse.urljoin("https://github.com/yondonfu/comfystream/releases/download/", f"v{version}/static.tar.gz")
    
    # Create a temporary directory instead of a temporary file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Define the path for the downloaded file
        download_path = os.path.join(temp_dir, "static.tar.gz")
        
        # Download tar.gz file
        logger.info(f"Downloading {base_url}")
        try:
            urllib.request.urlretrieve(base_url, download_path)
            
            # Extract contents
            logger.info(f"Extracting files to {output_dir}")
            with tarfile.open(download_path, 'r:gz') as tar:
                tar.extractall(path=output_dir)
        except Exception as e:
            logger.error(f"Error downloading or extracting files: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install custom node requirements")
    parser.add_argument(
        "--workspace", default=None, required=False, help="Set Comfy workspace"
    )
    args = parser.parse_args()
    
    workspace = args.workspace
    if workspace is None:
        # Look up to 3 directories up for ComfyUI
        current = os.getcwd()
        for _ in range(4):  # Check current dir + 3 levels up
            if os.path.exists(os.path.join(current, "comfy")):
                workspace = current
                logger.info(f"Found ComfyUI workspace at: {workspace}")
                break
            elif os.path.exists(os.path.join(current, "ComfyUI/comfy")):
                workspace = os.path.join(current, "ComfyUI")
                logger.info(f"Found ComfyUI workspace at: {workspace}")
                break
            elif os.path.exists(os.path.join(current, "comfyui/comfy")):
                workspace = os.path.join(current, "comfyui")
                logger.info(f"Found ComfyUI workspace at: {workspace}")
                break
            current = os.path.dirname(current)

    if workspace is None:
        logger.warning("No ComfyUI workspace found. Please specify a valid workspace path to fully install")

    logger.info("Downloading and extracting UI files...")
    version = get_project_version(os.getcwd())
    download_and_extract_ui_files(version)
    
    if workspace is not None:
        logger.info("Ensuring __init__.py files exist in ComfyUI directories...")
        ensure_init_files(workspace)
        logger.info("Installing custom node requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
    logger.info("Installation completed successfully.")
