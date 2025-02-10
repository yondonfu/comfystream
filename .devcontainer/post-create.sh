#!/bin/bash

# Install npm packages if needed
cd /workspace/comfystream/ui
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps   
fi

# Create a symlink to the ComfyUI workspace
if [ ! -d "/workspace/comfystream/ComfyUI" ]; then
    ln -s /workspace/ComfyUI /workspace/comfystream/ComfyUI
fi

cd /workspace/comfystream
/bin/bash