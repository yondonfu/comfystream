#!/bin/bash

# Initialize conda if needed
if ! command -v conda &> /dev/null; then
    /miniconda3/bin/conda init bash
fi

# Create a symlink to the ComfyUI workspace
if [ ! -d "/workspace/ComfyUI" ]; then
    ln -s /ComfyUI /workspace/ComfyUI
fi

/bin/bash