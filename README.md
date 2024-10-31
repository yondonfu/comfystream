# comfystream

comfystream is a package for running img2img [Comfy](https://www.comfy.org/) workflows on video streams.

This repo also includes a WebRTC server and UI that uses comfystream to support streaming from a webcam and processing the stream with a workflow JSON file (API format) created in ComfyUI. If you have an existing ComfyUI installation, the same custom nodes used to create the workflow in ComfyUI will be re-used when processing the video stream.

This project has only been tested locally with Linux + Nvidia GPUs.

- [comfystream](#comfystream)
- [Install package](#install-package)
  - [Custom Nodes](#custom-nodes)
  - [Usage](#usage)
- [Run server](#run-server)
- [Run UI](#run-ui)
- [Limitations](#limitations)

# Install package 

**Prerequisites**

- [Miniconda](https://docs.anaconda.com/miniconda/index.html#latest-miniconda-installer-links)
- [PyTorch](https://pytorch.org/get-started/locally/)

A separate environment can be used to avoid any dependency issues with an existing ComfyUI installation.

Create the environment:

```
conda create -n comfystream python=3.11
```

Activate the environment:

```
conda activate comfystream
```

Install `comfystream`:

```
pip install git+https://github.com/yondonfu/comfystream.git

# This can be used to install from a local repo
# pip install .
# This can be used to install from a local repo in edit mode
# pip install -e .
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

## Usage

See `example.py`.

# Run server

Install dependencies:

```
pip install -r requirements.txt
```

If you have existing custom nodes in your ComfyUI workspace, you will need to install their requirements in your current environment:

```
python install.py --workspace <COMFY_WORKSPACE>
```

Run the server:

```
python server/app.py --workspace <COMFY_WORKSPACE>
```

**Remote Setup**

A local server should connect with a local UI out-of-the-box. It is also possible to run a local UI and connect with a remote server, but there may be additional dependencies.

In order for the remote server to connect with another peer (i.e. a browser) without any additional dependencies you will need to allow inbound/outbound UDP traffic on ports 1024-65535 ([source](https://github.com/aiortc/aiortc/issues/490#issuecomment-788807118)). 

If you only have a subset of those UDP ports available, you can use the `--media-ports` flag to specify a comma delimited list of ports to use:

```
python server/app.py --workspace <COMFY_WORKSPACE> --media-ports 1024,1025,...
```

If you are running the server in a restrictive network environment where this is not possible, you will need to use a TURN server.

At the moment, the server supports using Twilio's TURN servers (although it is easy to make the update to support arbitrary TURN servers):

1. Sign up for a [Twilio](https://www.twilio.com/en-us) account.
2. Copy the Account SID and Auth Token from https://console.twilio.com/.
3. Set the `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` environment variables.

````
export TWILIO_ACCOUNT_SID=...
export TWILIO_AUTH_TOKEN=...
````

# Run UI

**Prerequisities**

- [Node.js](https://nodejs.org/en/download/package-manager)

Install dependencies

```
cd ui
npm install --legacy-peer-deps
```

Run local dev server:

```
npm run dev
```

By default the app will be available at http://localhost:3000.

# Limitations

At the moment, a workflow must fufill the following requirements:

- Single input using the LoadImage node
  - At runtime, this node is replaced with a LoadTensor node
- Single output using a PreviewImage or SaveImage node
  - At runtime, this node is replaced with a SaveTensor node