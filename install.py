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
import zipfile
from comfy_compatibility.workspace import auto_patch_workspace_and_restart

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

def download_and_extract_ui_files(version: str):
    """Download and extract UI files to the workspace"""

    output_dir = os.path.join(os.getcwd(), "nodes", "web", "static")
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    base_url = urllib.parse.urljoin("https://github.com/livepeer/comfystream/releases/download/", f"v{version}/comfystream-uikit.zip")
    fallback_url = "https://github.com/livepeer/comfystream/releases/latest/download/comfystream-uikit.zip"
    
    # Create a temporary directory instead of a temporary file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Define the path for the downloaded file
        download_path = os.path.join(temp_dir, "comfystream-uikit.zip")
        
        # Download zip file
        logger.info(f"Downloading {base_url}")
        try:
            urllib.request.urlretrieve(base_url, download_path)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.warning(f"{base_url} not found, trying {fallback_url}")
                try:
                    urllib.request.urlretrieve(fallback_url, download_path)
                except Exception as e:
                    logger.error(f"Error downloading latest ui package: {e}")
                    raise
            else:
                logger.error(f"Error downloading package: {e}")
                raise
        
        # Extract contents
        try:
            logger.info(f"Extracting files to {output_dir}")
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(path=output_dir)
        except Exception as e:
            logger.error(f"Error extracting files: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install custom node requirements")
    parser.add_argument(
        "--workspace", default=os.environ.get('COMFY_UI_WORKSPACE', None), required=False, help="Set Comfy workspace"
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

    logger.info("Installing comfystream package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])

    if workspace is None:
        logger.warning("No ComfyUI workspace found. Please specify a valid workspace path to fully install")
    
    if workspace is not None:
        logger.info("Patching ComfyUI workspace...")
        auto_patch_workspace_and_restart(workspace)
    
    logger.info("Downloading and extracting UI files...")
    version = get_project_version(os.getcwd())
    download_and_extract_ui_files(version)
    logger.info("Installation completed successfully.")
