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

# Add help command to show usage
show_help() {
  echo "Usage: entrypoint.sh [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --download-models       Download default models"
  echo "  --build-engines         Build TensorRT engines for default models"
  echo "  --server                Start the Comfystream server, UI and ComfyUI"
  echo "  --help                  Show this help message"
  echo ""
}

if [ "$1" = "--help" ]; then
  show_help
  exit 0
fi

if [ "$1" = "--download-models" ]; then
  cd /workspace/comfystream
  conda activate comfystream
  python src/comfystream/scripts/setup_models.py --workspace /workspace/ComfyUI
  shift
fi

DEPTH_ANYTHING_DIR="/workspace/ComfyUI/models/tensorrt/depth-anything"

if [ "$1" = "--build-engines" ]; then
  cd /workspace/comfystream
  conda activate comfystream

  # Build Static Engine for Dreamshaper
  python src/comfystream/scripts/build_trt.py --model /workspace/ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors --out-engine /workspace/ComfyUI/output/tensorrt/static-dreamshaper8_SD15_\$stat-b-1-h-512-w-512_00001_.engine

  # Build Engine for DepthAnything2
  if [ ! -f "$DEPTH_ANYTHING_DIR/depth_anything_vitl14-fp16.engine" ]; then
    if [ ! -d "$DEPTH_ANYTHING_DIR" ]; then
      mkdir -p "$DEPTH_ANYTHING_DIR"
    fi
    cd "$DEPTH_ANYTHING_DIR"
    python /workspace/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/export_trt.py
  else
    echo "Engine for DepthAnything2 already exists, skipping..."
  fi
  shift
fi

# Install npm packages if needed
cd /workspace/comfystream/ui
if [ ! -d "node_modules" ]; then
  npm install --legacy-peer-deps
fi

if [ "$1" = "--server" ]; then
  /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
  shift
fi

cd /workspace/comfystream

exec "$@"
