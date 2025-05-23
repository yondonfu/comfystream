#!/bin/bash

set -e
eval "$(conda shell.bash hook)"

if [ "$1" = "--server" ]; then
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

TENSORRT_DIR="/workspace/ComfyUI/models/tensorrt"
DEPTH_ANYTHING_DIR="${TENSORRT_DIR}/depth-anything"
DEPTH_ANYTHING_ENGINE="depth_anything_vitl14-fp16.engine"
DEPTH_ANYTHING_ENGINE_LARGE="depth_anything_v2_vitl-fp16.engine"
FASTERLIVEPORTRAIT_DIR="/workspace/ComfyUI/models/liveportrait_onnx"

if [ "$1" = "--build-engines" ]; then
  cd /workspace/comfystream
  conda activate comfystream

  # Build Static Engine for Dreamshaper - Square (512x512)
  python src/comfystream/scripts/build_trt.py --model /workspace/ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors --out-engine /workspace/ComfyUI/output/tensorrt/static-dreamshaper8_SD15_\$stat-b-1-h-512-w-512_00001_.engine --width 512 --height 512

  # Build Static Engine for Dreamshaper - Portrait (384x704)
  python src/comfystream/scripts/build_trt.py --model /workspace/ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors --out-engine /workspace/ComfyUI/output/tensorrt/static-dreamshaper8_SD15_\$stat-b-1-h-704-w-384_00001_.engine --width 384 --height 704

  # Build Static Engine for Dreamshaper - Landscape (704x384)
  python src/comfystream/scripts/build_trt.py --model /workspace/ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors --out-engine /workspace/ComfyUI/output/tensorrt/static-dreamshaper8_SD15_\$stat-b-1-h-384-w-704_00001_.engine --width 704 --height 384

  # Build Dynamic Engine for Dreamshaper
  python src/comfystream/scripts/build_trt.py \
                --model /workspace/ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors \
                --out-engine /workspace/ComfyUI/output/tensorrt/dynamic-dreamshaper8_SD15_\$dyn-b-1-4-2-h-512-704-w-320-384-448_00001_.engine \
                --width 384 \
                --height 704 \
                --min-width 320 \
                --min-height 512 \
                --max-width 448 \
                --max-height 704

  # Build Engine for Depth Anything V2
  if [ ! -f "$DEPTH_ANYTHING_DIR/$DEPTH_ANYTHING_ENGINE" ]; then
    if [ ! -d "$DEPTH_ANYTHING_DIR" ]; then
      mkdir -p "$DEPTH_ANYTHING_DIR"
    fi
    cd "$DEPTH_ANYTHING_DIR"
    python /workspace/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/export_trt.py
  else
    echo "Engine for DepthAnything2 already exists at ${DEPTH_ANYTHING_DIR}/${DEPTH_ANYTHING_ENGINE}, skipping..."
  fi

  # Build Engine for Depth Anything2 (large)
  if [ ! -f "$DEPTH_ANYTHING_DIR/$DEPTH_ANYTHING_ENGINE_LARGE" ]; then
    cd "$DEPTH_ANYTHING_DIR"
    python /workspace/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/export_trt.py --trt-path "${DEPTH_ANYTHING_DIR}/${DEPTH_ANYTHING_ENGINE_LARGE}" --onnx-path "${DEPTH_ANYTHING_DIR}/depth_anything_v2_vitl.onnx"
  else
    echo "Engine for DepthAnything2 (large) already exists at ${DEPTH_ANYTHING_DIR}/${DEPTH_ANYTHING_ENGINE_LARGE}, skipping..."
  fi

  # Build Engines for FasterLivePortrait
  if [ ! -f "$FASTERLIVEPORTRAIT_DIR/warping_spade-fix.trt" ]; then
    cd "$FASTERLIVEPORTRAIT_DIR"
    bash /workspace/ComfyUI/custom_nodes/ComfyUI-FasterLivePortrait/scripts/build_fasterliveportrait_trt.sh "${FASTERLIVEPORTRAIT_DIR}" "${FASTERLIVEPORTRAIT_DIR}" "${FASTERLIVEPORTRAIT_DIR}"
  else
    echo "Engines for FasterLivePortrait already exists, skipping..."
  fi

  # Build Engine for StreamDiffusion
  if [ ! -f "$TENSORRT_DIR/StreamDiffusion-engines/stabilityai/sd-turbo--lcm_lora-True--tiny_vae-True--max_batch-3--min_batch-3--mode-img2img/unet.engine.opt.onnx" ]; then
    cd /workspace/ComfyUI/custom_nodes/ComfyUI-StreamDiffusion
    MODELS="stabilityai/sd-turbo KBlueLeaf/kohaku-v2.1"
    TIMESTEPS="3"
    for model in $MODELS; do
      for timestep in $TIMESTEPS; do
        echo "Building model=$model with timestep=$timestep"
        python build_tensorrt.py \
          --model-id "$model" \
          --timesteps "$timestep" \
          --engine-dir $TENSORRT_DIR/StreamDiffusion-engines
      done
    done
  else
    echo "Engine for StreamDiffusion already exists, skipping..."
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
