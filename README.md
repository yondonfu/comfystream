# comfystream

- [comfystream](#comfystream)
- [Install package](#install-package)
  - [Custom Nodes](#custom-nodes)
  - [Usage](#usage)
- [Run server](#run-server)
- [Run UI](#run-ui)

# Install package 

Install PyTorch (optional):

```
pip install torch==2.4.1+cu121 torchvision torchaudio==2.4.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

Install xformers (optional):

```
pip install --no-build-isolation --no-deps xformers==0.0.28.post1 --index-url https://download.pytorch.org/whl/
```

The above installation commands are from [hiddenswitch/ComfyUI](https://github.com/hiddenswitch/ComfyUI/tree/master) and are marked optional because it should be possible to use an existing PyTorch installation as well.

Install `comfystream`:

```
pip install git+git@github.com:yondonfu/comfystream.git
```

## Custom Nodes

**tensor_utils**

Copy the `tensor_utils` nodes into the `custom_nodes` folder of your ComfyUI workspace:

```
cp -r nodes/tensor_utils custom_nodes
```

For example, if you ComfyUI workspace is under `/home/user/ComfyUI`:

```
cp -r nodes/tensor_utils /home/user/ComfyUI/custom_nodes
```

**Other**

In order to run workflows that involve other custom nodes, you will need to [install them](https://github.com/hiddenswitch/ComfyUI/tree/master?tab=readme-ov-file#custom-nodes).

## Usage

See `example.py`.

# Run server

```
pip install -r requirements.txt
```

```
python server/app.py --workspace <COMFY_WORKSPACE>
```

# Run UI

```
cd ui
npm install
```

```
npm run dev
```