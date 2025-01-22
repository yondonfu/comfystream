# Dev Container Setup for ComfyStream

This guide will help you set up and run a development container for ComfyStream using Visual Studio Code (VS Code).

## Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Visual Studio Code](https://code.visualstudio.com/)
- [VS Code Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Building the Base Container

To build the base container, run the following command in your terminal:

```sh
docker build -f .devcontainer/Dockerfile.base -t comfyui-base .
```

## Using the Pre-built Base Container

Most users will configure host paths for models in `devcontainer.json` and use the pre-built base container. Follow these steps:

1. Pull the pre-built base container:

    ```sh
    docker pull livepeer/comfyui-base
    ```

2. Configure the host paths for models in the `devcontainer.json` file.

3. Re-open the workspace in the dev container using VS Code:
    - Open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on macOS).
    - Select `Remote-Containers: Reopen in Container`.

## Configuration

Ensure your `devcontainer.json` is properly configured to map the necessary host paths for your models. Here is an example configuration:

```json
{
    "name": "ComfyStream Dev Container",
    "image": "livepeer/comfyui-base",
    "mounts": [
        "source=/path/to/your/models,target=/workspace/models,type=bind"
    ],
    "workspaceFolder": "/workspace"
}
```

Replace `/path/to/your/models` with the actual path to your models on the host machine.

## Additional Resources

- [Developing inside a Container](https://code.visualstudio.com/docs/remote/containers)
- [Docker Documentation](https://docs.docker.com/)

By following these steps, you should be able to set up and run your development container for ComfyStream efficiently.
## Building the DepthAnything Engine

1. Navigate to the DepthAnything directory:

    ```sh
    cd /ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/
    ```

2. Run the export script to build the engine and move the generated engine file to the appropriate directory:

    ```sh
    python export_trt.py
    mv depth_anything_vitl14-fp16.engine /ComfyUI/models/tensorrt/depth-anything/depth_anything_vitl14-fp16.engine
    ```

By following these steps, you will have successfully built and copied the DepthAnything engine to the required location.

3. Start ComfyUI

When building engines, you should start ComfyUI normally. 

```sh
python main.py --listen
```

When running TensorRT engine enabled workflows, you should use the extra flag as shown below:
```sh
python main.py --listen --disable-cuda-malloc
```

4. Start ComfyStream

    ```sh
    python server/app.py --workspace ../ComfyUI --media-ports=5678 --host=0.0.0.0 --port 8889
    ```