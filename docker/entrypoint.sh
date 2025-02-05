#!/bin/bash
set -e
eval "$(conda shell.bash hook)"

if [ "$1" = "--download-models" ]; then
    cd /comfystream
    conda activate comfystream
    python src/comfystream/scripts/setup_models.py --workspace /ComfyUI
    shift
fi

if [ "$1" = "--build-engines" ]; then
    cd /comfystream
    conda activate comfystream
    conda run -n comfystream --cwd /comfystream python src/comfystream/scripts/build_trt.py --model /ComfyUI/models/unet/dreamshaper-8-dmd-1kstep.safetensors --fp8 --out-engine /ComfyUI/models/tensorrt/static-dreamshaper8_SD15_$stat-b-1-h-512-w-512_00001_.engine
    shift
fi

if [ "$1" = "--run-comfystream" ]; then
    /usr/bin/supervisord
fi

exec "$@"