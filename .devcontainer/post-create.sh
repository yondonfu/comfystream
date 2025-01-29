#!/bin/bash

# Initialize conda if needed
if ! command -v conda &> /dev/null; then
    /miniconda3/bin/conda init bash
fi

# Install npm packages if needed
cd /workspace/ui
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps   
fi

# Create a symlink to the ComfyUI workspace
if [ ! -d "/workspace/ComfyUI" ]; then
    ln -s /ComfyUI /workspace/ComfyUI
fi

cd /workspace
/bin/bash