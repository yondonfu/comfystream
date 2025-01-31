# ComfyStream Model and Node Install Scripts

## Setup Scripts

1. **setup_nodes.py**: Installs custom ComfyUI nodes.
2. **setup_models.py**: Downloads model files and weights.

## Configuration Files

- `configs/nodes.yaml`: Defines custom nodes to install.
- `configs/models.yaml`: Defines model files to download.

## Basic Usage

From the repository root:

```bash
# Install both nodes and models (default workspace: ~/comfyui)
python src/comfystream/scripts/setup_nodes.py --workspace /path/to/workspace
python src/comfystream/scripts/setup_models.py --workspace /path/to/workspace
```

> The `--workspace` flag is optional and will default to `$COMFY_UI_WORKSPACE` or `~/comfyui`.

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

```sh
workspace/
├── custom_nodes/          # Custom nodes installed by setup-comfyui-nodes
└── models/               # Models downloaded by setup-comfyui-models
    ├── checkpoints/
    ├── controlnet/
    ├── unet/
    ├── vae/
    └── tensorrt/
```

## Environment Variables

- `COMFY_UI_WORKSPACE`: Base directory for installation
- `PYTHONPATH`: Defaults to workspace directory
- `CUSTOM_NODES_PATH`: Custom nodes directory
