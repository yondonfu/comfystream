# ComfyStream Setup Scripts

This directory contains scripts for setting up ComfyUI nodes and models. The setup is split into two main scripts:

## Setup Scripts

1. **setup-comfyui-nodes**: Installs custom ComfyUI nodes
2. **setup-comfyui-models**: Downloads model files and weights

## Configuration Files

- `configs/nodes.yaml`: Defines custom nodes to install
- `configs/models.yaml`: Defines model files to download
- `pyproject.toml`: Package dependencies and build settings

## Basic Usage

```bash
# Install both nodes and models (default workspace: ~/comfyui)
setup-comfyui-nodes
setup-comfyui-models

# Use custom workspace
setup-comfyui-nodes --workspace /path/to/workspace
setup-comfyui-models --workspace /path/to/workspace

# Using environment variable
export COMFY_UI_WORKSPACE=/path/to/workspace
setup-comfyui-nodes
setup-comfyui-models
```

## Configuration Examples

### Custom Nodes (nodes.yaml)
```yaml
nodes:
  comfyui-tensorrt:
    name: "ComfyUI TensorRT"
    url: "https://github.com/yondonfu/ComfyUI_TensorRT"
    type: "tensorrt"
    dependencies:
      - "tensorrt"
```

### Models (models.yaml)
```yaml
models:
  dreamshaper-v8:
    name: "Dreamshaper v8"
    url: "https://civitai.com/api/download/models/128713"
    path: "checkpoints/SD1.5/dreamshaper-8.safetensors"
    type: "checkpoint"
```

## Directory Structure

```
workspace/
├── custom_nodes/          # Custom nodes installed by setup-comfyui-nodes
└── models/               # Models downloaded by setup-comfyui-models
    ├── checkpoints/     
    ├── controlnet/      
    ├── unet/           
    ├── vae/            
    └── tensorrt/        
```

## Script Details

### setup-comfyui-nodes
- Clones node repositories from GitHub
- Installs node dependencies
- Creates custom_nodes directory
- Sets up environment variables

### setup-comfyui-models
- Downloads model weights
- Downloads additional files (configs, etc)
- Creates model directory structure
- Handles file verification

## Environment Variables

- `COMFY_UI_WORKSPACE`: Base directory for installation
- `PYTHONPATH`: Set to workspace directory
- `CUSTOM_NODES_PATH`: Custom nodes directory

## Notes

- Run both scripts to set up a complete environment
- Scripts can be run independently
- Both scripts use the same workspace configuration
- Models are only downloaded if they don't exist
- Node repositories are only cloned if not present
- Dependencies are installed automatically

## Troubleshooting

If you encounter issues:

1. Check if workspace directory is writable
2. Verify config files exist in configs/
3. Ensure Git is installed for node setup
4. Check network connection for downloads
5. Verify Python environment has required packages

## Testing

Run the installation tests:
```bash
python -m unittest tests/test_installation.py
```

This will verify:
- Directory structure
- Node installation
- Model downloads
- Environment setup