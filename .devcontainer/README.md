# Installation
## Build development container
```
cd .devcontainer && docker build -f Dockerfile.base -t comfystream:base .
 ```
### Create folders for models and custom nodes
```
mkdir -p $HOME/ComfyUI--models
mkdir -p $HOME/ComfyUI--nodes
```
Re-load `comfystream` folder as a devcontainer in vscode

### Install Nodes
From the devcontainer, run `which python` to make sure that you are not in a conda environment. 

If conda is activated then run `conda deactivate`
```
cd .devcontainer
./install-nodes.sh
```

### Build Tensorrt engines
From the devcontainer:
```
conda activate comfystream
cd .devcontainer 
./build-tensorrt.sh
```

# ComfyStream and ComfyUI
## Run ComfyStream
```
conda activate comfystream
cd /workspaces/comfystream
python server/app.py --workspace ../ComfyUI --media-ports=5678 --host=0.0.0.0
```

## Run ComfyUI
```
cd /workspaces/ComfyUI && python /workspaces/ComfyUI/main.py --listen
``` 
