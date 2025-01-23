#!/bin/bash

# Create a symlink to the extra_model_paths.yaml file only if /ComfyUI/extra/models exists and /ComfyUI/extra_model_paths.yaml does not exist, otherwise remove the link
if [ -d "/ComfyUI/extra/models" ] && [ ! -L "/ComfyUI/extra_model_paths.yaml" ]; then
    ln -s /workspace/.devcontainer/extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
else
    if [ -L "/ComfyUI/extra_model_paths.yaml" ]; then
        rm /ComfyUI/extra_model_paths.yaml
    fi
fi

# Initialize conda if needed
if ! command -v conda &> /dev/null; then
    /miniconda3/bin/conda init bash
fi

# Create a symlink to the ComfyUI workspace
if [ ! -d "/workspace/ComfyUI" ]; then
    ln -s /ComfyUI /workspace/ComfyUI
fi

/bin/bash