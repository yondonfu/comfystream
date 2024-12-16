#!/bin/bash
#NOTE: Run `conda activate comfystream` before running this script

if [[ "$(which python)" != *"conda"* ]]; then
    echo "Warning: Please ensure you have activated the correct environment with 'conda activate comfystream' before running this script."
    exit 1
fi

cd "/workspaces/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt"
wget -O depth_anything_vitl14.onnx https://huggingface.co/yuvraj108c/Depth-Anything-2-Onnx/resolve/main/depth_anything_v2_vitb.onnx?download=true
pip install -r requirements.txt
python export_trt.py
rm depth_anything_vitl14.onnx

#Copy engine to model directory for ComfyUI workspace
mkdir -p /workspaces/ComfyUI/models/tensorrt/depth-anything/
mv depth_anything_vitl14-fp16.engine /workspaces/ComfyUI/models/tensorrt/depth-anything/
