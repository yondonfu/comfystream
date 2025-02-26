import os
import subprocess
import argparse
import logging
import pathlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def install_custom_node_req(workspace: str):
    custom_nodes_path = os.path.join(workspace, "custom_nodes")
    if not os.path.exists(custom_nodes_path):
        logger.info("No custom nodes found.")
        return
    
    for folder in os.listdir(custom_nodes_path):
        folder_path = os.path.join(custom_nodes_path, folder)
        req_file = os.path.join(folder_path, "requirements.txt")

        if os.path.isdir(folder_path) and os.path.isfile(req_file):
            logger.info(f"Installing requirements for {folder}...")
            subprocess.run(["pip", "install", "-r", req_file], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install custom node requirements")
    parser.add_argument(
        "--workspace", default=os.getcwd(), required=False, help="Set Comfy workspace"
    )
    args = parser.parse_args()

    logger.info("Installing custom node requirements...")
    install_custom_node_req(args.workspace)
    
    logger.info("Ensuring __init__.py files exist in ComfyUI directories...")
    ensure_init_files(args.workspace)
    
    logger.info("Installation completed successfully.")
