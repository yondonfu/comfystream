# Dev Container Setup for ComfyStream

This guide will help you set up and run a development container for ComfyStream using Visual Studio Code (VS Code).

## Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Visual Studio Code](https://code.visualstudio.com/)
- [VS Code Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)



## Download or Build Base Docker Image
The `livepeer/comfyui-base:latest` image provides a ComfyUI workspace for ComfyStream development. You may either pull the base docker image or build it:

- Pull from Dockerhub:
```sh
docker pull livepeer/comfyui-base:latest
```
- Build the base image:
```sh
docker build -f docker/Dockerfile.base -t livepeer/comfyui-base:latest .
```

## Host Configuration
On your host system, create directories to store models and engines:

```sh
mkdir -p ~/models/ComfyUI--models && mkdir -p ~/models/ComfyUI--output
```
> **Note:** This step should be ran on your host machine before attempting to start the container


If you would like to use a different path to store models, open `devcontainer.json` and update the `source` to map to  the correct paths to your host system. Here is an example configuration:

```json
{
  "mounts": [
      "source=/path/to/your/model-files,target=/ComfyUI/models/ComfyUI--models,type=bind",
      "source=/path/to/your/output-files,target=/ComfyUI/models/ComfyUI--output,type=bind"
   ],
}
```

Replace `/path/to/your/model-files` and `path/to/your/output-files` with the path to your `models` and `output` folders on your host machine.

## Dev Container Setup

1. Clone the `comfystream` repository and open it in VS Code. 
2. From VS Code, reload the folder as a devcontainer:
   - Open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on macOS).
   - Select `Remote-Containers: Reopen in Container`.


### Download models
Download models to run the example workflows:

```sh
cd /workspace
python src/comfystream/scripts/setup_models.py --workspace /ComfyUI
```
For more info about configuring model downloads, see [src/comfystream/scripts/README.md](./src/comfystream/scripts/README.md)

By following these steps, you should be able to set up and run your development container for ComfyStream efficiently.

### Building the DepthAnything Engine

After downloading models, it is necessary to compile TensorRT engines for the example workflow. 

> [!NOTE]
> Engine files must be compiled on the same GPU hardware/architecture that are used on. This step must be ran manually after starting the devcontainer
> 


1. Run the **export_trt.py** script from the directory of the onnx file:

```sh
cd /ComfyUI/models/tensorrt/depth-anything
python /ComfyUI/custom_nodes/ComfyUI-Depth-Anything-Tensorrt/export_trt.py
```

> [!NOTE]
> You may use either conda environment for this step.

## Debugging ComfyStream and ComfyUI

The `launch.json` includes sample launch configurations for ComfyStream and ComfyUI. 

## Setting the Python Environment

Conda is not initited in the bash shell to provide better interoperabiltiy with VS Code Shell Integration. 

To launch a new terminal in either `comfystream` or `comfyui` environment: 
1. From VSCode, press `Ctrl-Shift-P`
2. Choose `Select Python Interpreter`
3. Select `comfystream` or `comfyui`
4. Open a new terminal, you will see the environment name to the left of the bash terminal.

> [!NOTE] NOTE For more information, see [Python environments in VS Code](https://code.visualstudio.com/docs/python/environments)



### Starting ComfyUI
Start ComfyUI:
```sh
cd /workspace/ComfyUI
python main.py --listen
```

When using TensorRT engine enabled workflows, you should include the `---disable-cuda-malloc` flag as shown below:

```sh
cd /workspace/ComfyUI
python main.py --listen --disable-cuda-malloc
```

### Starting ComfyStream

```sh
cd /workspace
python server/app.py --workspace /ComfyUI --media-ports=5678 --host=0.0.0.0 --port 8888
```

## Additional Resources

- [Developing inside a Container](https://code.visualstudio.com/docs/remote/containers)
- [Docker Documentation](https://docs.docker.com/)
