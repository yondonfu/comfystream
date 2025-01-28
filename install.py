import os
import subprocess
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_custom_node_req(workspace: str):
    custom_nodes_path = os.path.join(workspace, "custom_nodes")
    for folder in os.listdir(custom_nodes_path):
        folder_path = os.path.join(custom_nodes_path, folder)
        req_file = os.path.join(folder_path, "requirements.txt")

        if os.path.isdir(folder_path) and os.path.isfile(req_file):
            logger.info(f"Installing requirements for {folder}...")
            subprocess.run(["pip", "install", "-r", req_file], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install custom node requirements")
    parser.add_argument(
        "--workspace", default=None, required=True, help="Set Comfy workspace"
    )
    args = parser.parse_args()

    logger.info("Installing custom node requirements...")
    install_custom_node_req(args.workspace)
    logger.info("Custom node requirements installed successfully.")
