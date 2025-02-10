#!/bin/bash
set -e
eval "$(conda shell.bash hook)"

if [ "$1" = "--download-models" ]; then
    cd /workspace/comfystream
    conda activate comfystream
    python src/comfystream/scripts/setup_models.py --workspace /workspace/ComfyUI
    shift
fi

if [ "$1" = "--build-engines" ]; then
    cd /workspace/comfystream
    conda activate comfystream
    python src/comfystream/scripts/build_trt.py --model /workspace/ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors --out-engine /workspace/ComfyUI/models/tensorrt/static-dreamshaper8_SD15_\$stat-b-1-h-512-w-512_00001_.engine
    shift
fi

if [ "$1" = "--server" ]; then
    /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
fi
