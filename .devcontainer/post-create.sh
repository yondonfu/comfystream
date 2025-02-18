#!/bin/bash

chmod +x /workspace/comfystream/docker/entrypoint.sh
cd /workspace/comfystream

# Install Comfystream in editable mode.
/workspace/comfystream/docker/entrypoint.sh --editable

# Create a symlink to the entrypoint script.
echo 'alias prepare_examples="/workspace/comfystream/docker/entrypoint.sh --download-models --build-engines"' >> ~/.bashrc
echo -e "\e[32mContainer ready! Run 'prepare_examples' to download models and build engines for example workflows.\e[0m"

/bin/bash
