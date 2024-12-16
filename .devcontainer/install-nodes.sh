#!/bin/bash

if [[ "$(which python)" == *"conda"* ]]; then
    echo "Warning: Please ensure you have activated the correct environment. Run 'conda deactivate' before running this script."
    exit 1
fi

# Copy ComfyStream custom nodes to ComfyUI
cp -r /workspaces/comfystream/nodes/tensor_utils /workspaces/ComfyUI/custom_nodes

# Install ComfyStream requirements
cd /workspaces/comfystream && /root/miniconda3/envs/comfystream/bin/pip install .

cd /workspaces/ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
git clone https://github.com/ryanontheinside/ComfyUI-Misc-Effects.git

if [ ! -d "/workspaces/ComfyUI/custom_nodes/ComfyUI-SAM2-Realtime" ]; then
    git clone https://github.com/pschroedl/ComfyUI-SAM2-Realtime.git
    cd /workspaces/ComfyUI/custom_nodes/ComfyUI-SAM2-Realtime 

    # Install requirements as ComfyUI
    pip install -r requirements.txt

    # Install requirements as ComfyStream
    /root/miniconda3/envs/comfystream/bin/pip install -r requirements.txt
    cd ..
else
    echo "Directory /workspaces/ComfyUI/custom_nodes/ComfyUI-SAM2-Realtime already exists. Skipping clone and requirements install."
fi

if [ ! -d "/workspaces/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt" ]; then
    git clone https://github.com/yuvraj108c/ComfyUI-Depth-Anything-Tensorrt.git
    cd ComfyUI-Depth-Anything-Tensorrt 

    # Install requirements as ComfyUI
    pip install -r requirements.txt

    # Install requirements as ComfyStream
    /root/miniconda3/envs/comfystream/bin/pip install -r requirements.txt
    cd ..
else
    echo "Directory /workspaces/ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt already exists. Skipping clone and requirements install."
fi

if [ ! -d "/workspaces/ComfyUI/custom_nodes/ComfyUI_RyanOnTheInside" ]; then
    git clone https://github.com/ryanontheinside/ComfyUI_RyanOnTheInside.git
    cd ComfyUI_RyanOnTheInside

    # Install requirements as ComfyUI
    pip install -r requirements.txt

    cd ..
else
    echo "Directory /workspaces/ComfyUI/custom_nodes/ComfyUI_RyanOnTheInside already exists. Skipping clone and requirements install."
fi

# Add additonal nodes here
