#!/bin/bash

# Install npm packages if needed
cd /comfystream/ui
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps   
fi

# Create a symlink to the ComfyUI workspace
if [ ! -d "/comfystream/ComfyUI" ]; then
    ln -s /ComfyUI /comfystream/ComfyUI
fi

cd /comfystream
/bin/bash