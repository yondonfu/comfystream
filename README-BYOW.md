# Bring Your Own ComfyUI Workspace

This Dockerfile (`Dockerfile.byow`) allows you to run ComfyStream with your own ComfyUI workspace, preserving all your custom nodes, models, and configurations.

## Features

- **Workspace Preservation**: Mount your existing ComfyUI workspace with all customizations
- **Automatic venv Management**: Creates and manages a `uv` virtual environment in your workspace
- **Flexible Setup**: Works with existing ComfyUI installations or initializes new ones
- **ComfyStream Integration**: Automatically installs the comfystream node
- **No File Dependencies**: Container doesn't require any files from the build context

## Usage

### Building the Image

```bash
# Build the bring-your-own-workspace image
docker build -f Dockerfile.byow -t comfystream:byow .
```

### Running with Your Workspace

#### Option 1: Mount Existing ComfyUI Workspace

```bash
# Run with your existing ComfyUI workspace
docker run -it --rm \
    --gpus all \
    -p 8188:8188 \
    -v /path/to/your/comfyui:/workspace/ComfyUI \
    comfystream:byow
```

#### Option 2: Initialize New Workspace

```bash
# Create a new directory for ComfyUI workspace
mkdir -p ~/comfyui-workspace

# Run and let the container initialize ComfyUI
docker run -it --rm \
    --gpus all \
    -p 8188:8188 \
    -v ~/comfyui-workspace:/workspace/ComfyUI \
    comfystream:byow
```

#### Option 3: Development Mode with Shell Access

```bash
# Run with shell access for development
docker run -it --rm \
    --gpus all \
    -p 8188:8188 \
    -v /path/to/your/comfyui:/workspace/ComfyUI \
    comfystream:byow \
    bash
```

### Advanced Usage

#### Custom ComfyUI Arguments

```bash
# Run ComfyUI with custom arguments
docker run -it --rm \
    --gpus all \
    -p 8188:8188 \
    -v /path/to/your/comfyui:/workspace/ComfyUI \
    comfystream:byow \
    python main.py --listen 0.0.0.0 --port 8188 --output-directory /workspace/ComfyUI/output
```

#### Running comfy-cli Commands

```bash
# Install additional nodes
docker run -it --rm \
    --gpus all \
    -v /path/to/your/comfyui:/workspace/ComfyUI \
    comfystream:byow \
    comfy node install <node-name>

# Update ComfyUI
docker run -it --rm \
    --gpus all \
    -v /path/to/your/comfyui:/workspace/ComfyUI \
    comfystream:byow \
    comfy update
```

## How It Works

1. **Container Initialization**: The container starts with a clean ComfyUI environment
2. **Workspace Detection**: Checks if the mounted volume contains a valid ComfyUI installation
3. **Environment Setup**: Creates or uses existing `.venv` in your workspace using `uv`
4. **Dependency Management**: All packages are installed in the workspace's virtual environment
5. **ComfyStream Integration**: Automatically installs the comfystream custom node
6. **Service Start**: Starts ComfyUI server or runs your specified command

## Workspace Structure

Your ComfyUI workspace should follow this structure:

```
/path/to/your/comfyui/
├── .venv/                 # Virtual environment (auto-created if missing)
├── custom_nodes/          # Your custom nodes
├── models/               # Your models
├── input/                # Input files
├── output/               # Generated outputs
├── main.py              # ComfyUI main script
└── requirements.txt     # Python dependencies (optional)
```

## Environment Variables

The container sets these environment variables for optimal performance:

- `PYTORCH_CUDA_ALLOC_CONF="backend:cudaMallocAsync,expandable_segments:True"`
- `UV_COMPILE_BYTECODE=1` - Compile Python bytecode for faster imports
- `UV_NO_CACHE=1` - Disable uv cache in container
- `UV_SYSTEM_PYTHON=1` - Use system Python with uv

## Ports

- `8188`: ComfyUI web interface and API

## Health Check

The container includes a health check that verifies the ComfyUI server is responding:

```bash
curl -f http://localhost:8188/system_stats
```

## Troubleshooting

### Permission Issues

If you encounter permission issues, ensure your local ComfyUI directory has appropriate permissions:

```bash
sudo chown -R $(whoami):$(whoami) /path/to/your/comfyui
chmod -R 755 /path/to/your/comfyui
```

### Virtual Environment Issues

If the virtual environment setup fails, you can manually recreate it:

```bash
# Remove existing venv and let container recreate it
rm -rf /path/to/your/comfyui/.venv

# Run container again
docker run -it --rm --gpus all -p 8188:8188 -v /path/to/your/comfyui:/workspace/ComfyUI comfystream:byow
```

### Missing ComfyStream Node

If the comfystream node isn't available, manually install it:

```bash
docker run -it --rm \
    --gpus all \
    -v /path/to/your/comfyui:/workspace/ComfyUI \
    comfystream:byow \
    comfy node registry-install comfystream
```
