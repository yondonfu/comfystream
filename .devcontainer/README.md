# Dev Container Setup for ComfyStream

This guide will help you set up and run a development container for ComfyStream using Visual Studio Code (VS Code).

## Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Visual Studio Code](https://code.visualstudio.com/)
- [VS Code Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Building the Base Container

To build the base container, run the following command in your terminal:

```sh
docker build -f .devcontainer/Dockerfile.base -t livepeer/comfyui-base:latest .
```

## Using the Pre-built Base Container

Most users will configure host paths for models in `devcontainer.json` and use the pre-built base container. Follow these steps:

1. Pull the pre-built base container:

```sh
docker pull livepeer/comfyui-base:latest
```

2. Configure the host paths for models in the `devcontainer.json` file.

3. Re-open the workspace in the dev container using VS Code:
    - Open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on macOS).
    - Select `Remote-Containers: Reopen in Container`.

## Configuration

Create a directory to store the models
```sh
sudo mkdir -p /models/ComfyUI--models && sudo chown -R $USER /models/ComfyUI--models
```

If you have a different path for models, ensure your `devcontainer.json` is properly configured to map the correct host path to your models. Here is an example configuration:

```json
{
    "name": "ComfyStream Dev Container",
    "image": "livepeer/comfyui-base",
    "mounts": [
        "source=/path/to/your/models,target=/ComfyUI/models,type=bind"
    ],
    "workspaceFolder": "/workspace"
}
```

Replace `/path/to/your/models` with the actual path to your models on the host machine.

### Download models

```sh
cd /workspace
python src/comfystream/scripts/setup_models.py --workspace /ComfyUI
```

By following these steps, you should be able to set up and run your development container for ComfyStream efficiently.
## Building the DepthAnything Engine

1. Run the **export_trt.py** script from the directory of the onnx file:

```sh
cd /ComfyUI/models/tensorrt/depth-anything
python /ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/export_trt.py
```

**Note**: You may use either conda environment for this step

### Starting ComfyUI

When building engines, you should start ComfyUI normally. 

```sh
python main.py --listen
```

When running TensorRT engine enabled workflows, you should use the extra flag as shown below:
```sh
python main.py --listen --disable-cuda-malloc
```

### Starting ComfyStream

```sh
python server/app.py --workspace /ComfyUI --media-ports=5678 --host=0.0.0.0 --port 8889
```

## Additional Resources

- [Developing inside a Container](https://code.visualstudio.com/docs/remote/containers)
- [Docker Documentation](https://docs.docker.com/)
- [Activate-Environments-in-Terminal-Using-Environment-Variables](https://github.com/microsoft/vscode-python/wiki/Activate-Environments-in-Terminal-Using-Environment-Variables)
