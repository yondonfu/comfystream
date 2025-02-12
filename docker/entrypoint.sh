#!/bin/bash
set -e
eval "$(conda shell.bash hook)"

# Handle workspace mounting
if [ -d "/app" ] && [ ! -d "/app/miniconda3" ]; then
    echo "Initializing workspace in /app..."
    cp -r /workspace/* /app
fi

if [ -d "/app" ] && [ ! -L "/workspace" ]; then
    echo "Starting from volume mount /app..."
    cd / && rm -rf /workspace
    ln -sf /app /workspace
    cd /workspace/comfystream
fi

if [ "$1" = "--download-models" ]; then
    cd /workspace/comfystream
    conda activate comfystream
    python src/comfystream/scripts/setup_models.py --workspace /workspace/ComfyUI
    shift
fi

if [ "$1" = "--build-engines" ]; then
    cd /workspace/comfystream
    conda activate comfystream

    # Build Static Engine for Dreamshaper 
    python src/comfystream/scripts/build_trt.py --model /workspace/ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors --out-engine /workspace/ComfyUI/output/tensorrt/static-dreamshaper8_SD15_\$stat-b-1-h-512-w-512_00001_.engine

    # Build Engine for DepthAnything2
    if [ ! -d "/workspace/ComfyUI/models/tensorrt/depth-anything" ]; then
        mkdir -p /workspace/ComfyUI/models/tensorrt/depth-anything
    fi
    cd /workspace/ComfyUI/models/tensorrt/depth-anything
    python /workspace/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/export_trt.py
    shift
fi

# Install npm packages if needed
cd /workspace/comfystream/ui
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps
fi

if [ "$1" = "--server" ]; then
    /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
fi

cd /workspace/comfystream
/bin/bash