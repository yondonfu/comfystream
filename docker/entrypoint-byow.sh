#!/bin/bash
set -e

echo "Setting up ComfyUI workspace..."

comfy set-default /workspace/ComfyUI
# # Check if /workspace/ComfyUI is a symlink (indicating mounted volume)
# if [[ -L "/workspace/ComfyUI" ]]; then
#     echo "Detected mounted workspace (symlink found)"

#     cd /workspace/ComfyUI

#     # Check if ComfyUI is already installed in the mounted workspace
#     if [[ -f "main.py" ]]; then
#         echo "ComfyUI installation found in mounted workspace, restoring..."
#         # Ensure .venv exists in the workspace
#         if [[ ! -d ".venv" ]]; then
#             echo "Creating virtual environment in workspace..."
#             uv venv .venv
#         fi

#         # Activate the virtual environment
#         echo "Activating virtual environment..."
#         source .venv/bin/activate

#         # Ensure comfy-cli is available in the venv
#         if ! command -v comfy &> /dev/null; then
#             echo "Installing comfy-cli in workspace venv..."
#             uv pip install comfy-cli
#         fi

#         # Restore the existing ComfyUI workspace
#         echo "Restoring ComfyUI workspace..."
#         comfy --skip-prompt --here install --nvidia --restore --skip-requirement

#     else
#         echo "No ComfyUI installation found in mounted workspace, installing..."

#         # Install ComfyUI in the mounted workspace
#         comfy --skip-prompt --here install --nvidia

#         # Ensure .venv exists in the workspace
#         if [[ ! -d ".venv" ]]; then
#             echo "Creating virtual environment in workspace..."
#             uv venv .venv
#         fi

#         # Activate the virtual environment
#         echo "Activating virtual environment..."
#         source .venv/bin/activate

#         # Ensure comfy-cli is available in the venv
#         if ! command -v comfy &> /dev/null; then
#             echo "Installing comfy-cli in workspace venv..."
#             uv pip install comfy-cli
#         fi
#     fi

#     # Install comfystream node if not already installed
#     if [[ ! -d "custom_nodes/comfystream" ]]; then
#         echo "Installing comfystream node..."
#         comfy node registry-install comfystream
#     fi

# else
#     echo "Using built-in ComfyUI workspace (no mount detected)"
#     cd /workspace/ComfyUI

#     # Activate the pre-built virtual environment
#     echo "Activating virtual environment..."
#     source .venv/bin/activate
# fi

# Set up completion if not already done
if [[ ! -f ~/.local/share/bash-completion/completions/comfy ]]; then
    comfy --install-completion 2>/dev/null || true
fi

echo "ComfyUI workspace setup complete!"


# Execute the command passed to docker run, or start ComfyUI by default
if [[ $# -eq 0 ]]; then
    echo "Starting ComfyUI server..."
    exec comfy launch -- --listen 0.0.0.0 --port 8188 --front-end-version Comfy-Org/ComfyUI_frontend@v1.24.2
else
    exec "$@"
fi
