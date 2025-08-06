# ComfyStream Model and Node Install Scripts

## Setup Scripts

1. **setup_nodes.py**: Installs custom ComfyUI nodes.
2. **setup_models.py**: Downloads model files and weights.

## Configuration Files

- `configs/nodes.yaml`: Defines custom nodes to install.
- `configs/models.yaml`: Defines model files to download.

## Basic Usage

From the repository root:

> The `--workspace` flag is optional and will default to `$COMFY_UI_WORKSPACE` or `~/comfyui`.

### Install custom nodes
```bash
python src/comfystream/scripts/setup_nodes.py --workspace /path/to/comfyui
```
> The optional flag `--pull-branches` can be used to ensure the latest git changes are pulled for any custom nodes defined with a `branch` in nodes.yaml

### Download models and compile tensorrt engines
```bash
python src/comfystream/scripts/setup_models.py --workspace /path/to/comfyui
```

## Configuration Examples

### Custom Nodes (nodes.yaml)

```yaml
nodes:
  comfyui-tensorrt:
    name: "ComfyUI TensorRT"
    url: "https://github.com/yondonfu/ComfyUI_TensorRT"
    type: "tensorrt"
    branch: "master"
    dependencies:
      - "tensorrt"
```

> The `branch` property can be substituted with a SHA-256 commit hash for pinning custom node versions 

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
