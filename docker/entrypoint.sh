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
  echo "  --opencv-cuda           Setup OpenCV with CUDA support"
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

  # Build Dynamic Engine for Dreamshaper
  python src/comfystream/scripts/build_trt.py \
                --model /workspace/ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors \
                --out-engine /workspace/ComfyUI/output/tensorrt/dynamic-dreamshaper8_SD15_\$dyn-b-1-4-2-h-448-704-512-w-448-704-512_00001_.engine \
                --width 512 \
                --height 512 \
                --min-width 448 \
                --min-height 448 \
                --max-width 704 \
                --max-height 704

  # Build Engine for Depth Anything V2
  if [ ! -f "$DEPTH_ANYTHING_DIR/depth_anything_vitl14-fp16.engine" ]; then
    if [ ! -d "$DEPTH_ANYTHING_DIR" ]; then
      mkdir -p "$DEPTH_ANYTHING_DIR"
    fi
    cd "$DEPTH_ANYTHING_DIR"
    python /workspace/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/export_trt.py
  else
    echo "Engine for DepthAnything2 already exists, skipping..."
  fi

  # Build Engine for Depth Anything2 (large)
  if [ ! -f "$DEPTH_ANYTHING_DIR/depth_anything_v2_vitl-fp16.engine" ]; then
    cd "$DEPTH_ANYTHING_DIR"
    python /workspace/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/export_trt.py --trt-path "${DEPTH_ANYTHING_DIR}/depth_anything_v2_vitl-fp16.engine" --onnx-path "${DEPTH_ANYTHING_DIR}/depth_anything_v2_vitl.onnx"
  else
    echo "Engine for DepthAnything2 (large) already exists, skipping..."
  fi
  shift
fi

if [ "$1" = "--opencv-cuda" ]; then
  cd /workspace/comfystream
  conda activate comfystream
  
  # Check if OpenCV CUDA build already exists
  if [ ! -f "/workspace/comfystream/opencv-cuda-release.tar.gz" ]; then
    # Download and extract OpenCV CUDA build
    DOWNLOAD_NAME="opencv-cuda-release.tar.gz"
    wget -q -O "$DOWNLOAD_NAME" https://github.com/JJassonn69/ComfyUI-Stream-Pack/releases/download/v1.0/opencv-cuda-release.tar.gz
    tar -xzf "$DOWNLOAD_NAME" -C /workspace/comfystream/
    rm "$DOWNLOAD_NAME"
  else
    echo "OpenCV CUDA build already exists, skipping download."
  fi

  # Install required libraries
  apt-get update && apt-get install -y \
    libgflags-dev \
    libgoogle-glog-dev \
    libjpeg-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev

  # Remove existing cv2 package
  SITE_PACKAGES_DIR="/workspace/miniconda3/envs/comfystream/lib/python3.11/site-packages"
  rm -rf "${SITE_PACKAGES_DIR}/cv2"*

  # Copy new cv2 package
  cp -r /workspace/comfystream/cv2 "${SITE_PACKAGES_DIR}/"

  # Handle library dependencies
  CONDA_ENV_LIB="/workspace/miniconda3/envs/comfystream/lib"
  
  # Remove existing libstdc++ and copy system one
  rm -f "${CONDA_ENV_LIB}/libstdc++.so"*
  cp /usr/lib/x86_64-linux-gnu/libstdc++.so* "${CONDA_ENV_LIB}/"

  # Copy OpenCV libraries
  cp /workspace/comfystream/opencv/build/lib/libopencv_* /usr/lib/x86_64-linux-gnu/

  # remove the opencv-contrib and cv2 folders
  rm -rf /workspace/comfystream/opencv_contrib
  rm -rf /workspace/comfystream/cv2

  echo "OpenCV CUDA installation completed"
  shift
fi

if [ "$1" = "--server" ]; then
  /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
  shift
fi

cd /workspace/comfystream

exec "$@"
