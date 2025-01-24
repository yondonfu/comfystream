#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import requests
from tqdm import tqdm
import yaml
import argparse
from utils import get_config_path, load_model_config

def parse_args():
    parser = argparse.ArgumentParser(description='Setup ComfyUI models')
    parser.add_argument('--workspace', 
                       default=os.environ.get('COMFY_UI_WORKSPACE', os.path.expanduser('~/comfyui')),
                       help='ComfyUI workspace directory (default: ~/comfyui or $COMFY_UI_WORKSPACE)')
    return parser.parse_args()

def download_file(url, destination, description=None):
    """Download a file with progress bar"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    desc = description or os.path.basename(destination)
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True, desc=desc)
    
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    with open(destination, 'wb') as file:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            progress_bar.update(size)
    progress_bar.close()

def setup_model_files(workspace_dir, config_path=None):
    """Download and setup required model files based on configuration"""
    if config_path is None:
        config_path = get_config_path('models.yaml')
    try:
        config = load_model_config(config_path)
    except FileNotFoundError:
        print(f"Error: Model config file not found at {config_path}")
        return
    except yaml.YAMLError as e:
        print(f"Error parsing model config file: {e}")
        return

    models_path = workspace_dir / "models"
    base_path = workspace_dir

    for model_id, model_info in config['models'].items():
        # Determine the full path based on whether it's in custom_nodes or models
        if model_info['path'].startswith('custom_nodes/'):
            full_path = base_path / model_info['path']
        else:
            full_path = models_path / model_info['path']

        if not full_path.exists():
            print(f"Downloading {model_info['name']}...")
            download_file(
                model_info['url'],
                full_path,
                f"Downloading {model_info['name']}"
            )
            print(f"Downloaded {model_info['name']} to {full_path}")

            # Handle any extra files (like configs)
            if 'extra_files' in model_info:
                for extra in model_info['extra_files']:
                    extra_path = models_path / extra['path']
                    if not extra_path.exists():
                        download_file(
                            extra['url'],
                            extra_path,
                            f"Downloading {os.path.basename(extra['path'])}"
                        )
    print("Models download completed!")

def setup_directories(workspace_dir):
    """Create required directories in the workspace"""
    # Create base directories
    workspace_dir.mkdir(parents=True, exist_ok=True)
    models_dir = workspace_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Create model subdirectories
    model_dirs = [
        "checkpoints/SD1.5",
        "controlnet",
        "vae",
        "tensorrt",
        "unet",
    ]
    for dir_name in model_dirs:
        (models_dir / dir_name).mkdir(parents=True, exist_ok=True)

def main():
    args = parse_args()
    workspace_dir = Path(args.workspace)
    
    setup_directories(workspace_dir)
    setup_model_files(workspace_dir)

if __name__ == "__main__":
    main() 