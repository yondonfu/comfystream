#!/bin/bash

chmod +x /workspace/comfystream/docker/entrypoint.sh
cd /workspace/comfystream

# Install Comfystream in editable mode.
echo -e "\e[32mInstalling Comfystream in editable mode...\e[0m"
/workspace/miniconda3/envs/comfystream/bin/python3 -m pip install -e . --root-user-action=ignore > /dev/null

# Install npm packages if needed
if [ ! -d "/workspace/comfystream/ui/node_modules" ]; then
    echo -e "\e[32mInstalling npm packages for Comfystream UI...\e[0m"
    cd /workspace/comfystream/ui
    npm install
fi

if [ ! -d "/workspace/comfystream/nodes/web/static" ]; then
    echo -e "\e[32mBuilding web assets...\e[0m"
    cd /workspace/comfystream/ui
    npm install
    # removed it as we are already getting the built files from install.py
fi

# Create a symlink to the entrypoint script.
echo 'alias prepare_examples="/workspace/comfystream/docker/entrypoint.sh --download-models --build-engines"' >> ~/.bashrc
echo -e "\e[32mContainer ready! Run 'prepare_examples' to download models and build engines for example workflows.\e[0m"

cd /workspace/comfystream

# Ensure git doesn't complain about comfystream directory ownership
git config --global --add safe.directory /workspace/comfystream

# Print final success message
echo -e "\e[32mDevelopment environment setup complete!\e[0m"

