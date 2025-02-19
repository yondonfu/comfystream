#!/bin/bash

chmod +x /workspace/comfystream/.devcontainer/entrypoint.sh
cd /workspace/comfystream

# Install Comfystream in editable mode.
echo -e "\e[32mInstalling Comfystream in editable mode...\e[0m"
/workspace/miniconda3/envs/comfystream/bin/python3 -m pip install -e . > /dev/null

# Create a symlink to the entrypoint script.
echo 'alias prepare_examples="/workspace/comfystream/.devcontainer/entrypoint.sh --download-models --build-engines"' >> ~/.bashrc
echo -e "\e[32mContainer ready! Run 'prepare_examples' to download models and build engines for example workflows.\e[0m"

/bin/bash
