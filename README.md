# comfystream

> [!IMPORTANT]
> This repository serves as the stable upstream for the ComfyStream project. Active development has moved to the [Livepeer fork](https://github.com/livepeer/comfystream), though stable versions are still merged here.

ComfyStream is a package for running img2img [Comfy](https://www.comfy.org/) workflows on video streams.

This repo also includes a WebRTC server and UI that uses comfystream to support streaming from a webcam and processing the stream with a workflow JSON file (API format) created in ComfyUI. If you have an existing ComfyUI installation, the same custom nodes used to create the workflow in ComfyUI will be re-used when processing the video stream.

- [comfystream](#comfystream)
  - [Quick Start](#quick-start)
    - [Docker DevContainer](#docker-devcontainer)
    - [Docker Image](#docker-image)
      - [RunPod](#runpod)
      - [Tensordock](#tensordock)
      - [Other Cloud Providers](#other-cloud-providers)
  - [Download Models](#download-models)
  - [Install package](#install-package)
    - [Custom Nodes](#custom-nodes)
    - [Usage](#usage)
  - [Run tests](#run-tests)
  - [Run server](#run-server)
  - [Run UI](#run-ui)
  - [Limitations](#limitations)
  - [Troubleshoot](#troubleshoot)

## Quick Start

### Docker DevContainer

Refer to [.devcontainer/README.md](.devcontainer/README.md) to setup ComfyStream in a devcontainer using a pre-configured ComfyUI docker environment.

For other installation options, refer to [Install ComfyUI and ComfyStream](https://docs.comfystream.org/technical/get-started/install) in the ComfyStream documentation.

For additional information, refer to the remaining sections below.

### Docker Image

You can quickly deploy ComfyStream using the docker image `livepeer/comfystream`

Refer to the documentation at [https://docs.comfystream.org/technical/get-started/install](https://docs.comfystream.org/technical/get-started/install) for instructions to run locally or on a remote server.

#### RunPod

The RunPod template [livepeer-comfystream](https://runpod.io/console/deploy?template=w01m180vxx&ref=u8tlskew) can be used to deploy to RunPod.

#### Tensordock

We also have a python script that can be used to spin up a ComfyStream instance on a [Tensordock server](https://tensordock.com/). Refer to [scripts/README.md](./scripts/README.md#tensordock-auto-setup-fully-automated) for instructions.

#### Other Cloud Providers

We also provide an [Ansible playbook](https://docs.ansible.com/ansible/latest/installation_guide/index.html) for deploying ComfyStream on any cloud provider. Refer to [scripts/README.md](./scripts/README.md#cloud-agnostic-automated-setup-ansible-based-deployment) for instructions.

## Download Models

Refer to [scripts/README.md](src/comfystream/scripts/README.md) for instructions to download commonly used models.

## Install package

**Prerequisites**

- [Miniconda](https://docs.anaconda.com/miniconda/index.html#latest-miniconda-installer-links)

A separate environment can be used to avoid any dependency issues with an existing ComfyUI installation.

Create the environment:

```bash
conda create -n comfystream python=3.12
```

Activate the environment:

```bash
conda activate comfystream
```

Make sure you have [PyTorch](https://pytorch.org/get-started/locally/) installed.

Install `comfystream`:

```bash
pip install git+https://github.com/livepeer/comfystream.git

# This can be used to install from a local repo
# pip install .
# This can be used to install from a local repo in edit mode
# pip install -e .
```

### Custom Nodes

Comfystream uses a few auxiliary custom nodes to support running workflows.

**Note:** If you are using comfystream as a custom node in ComfyUI, you can skip the following steps.

If you are using comfystream as a standalone application, copy the auxiliary custom nodes into the `custom_nodes` folder of your ComfyUI workspace:

```bash
cp -r nodes/* custom_nodes/
```

For example, if your ComfyUI workspace is under `/home/user/ComfyUI`:

```bash
cp -r nodes/* /home/user/ComfyUI/custom_nodes
```

### Usage

See `example.py`.

## Run tests

Install dev dependencies:

```bash
pip install .[dev]
```

Run tests:

```bash
pytest
```

## Run server

Install dependencies:

```bash
pip install -r requirements.txt
```

If you have existing custom nodes in your ComfyUI workspace, you will need to install their requirements in your current environment:

```bash
python install.py --workspace <COMFY_WORKSPACE>
```

Run the server:

```bash
python server/app.py --workspace <COMFY_WORKSPACE>
```

Show additional options for configuring the server:

```bash
python server/app.py -h
```

**Remote Setup**

A local server should connect with a local UI out-of-the-box. It is also possible to run a local UI and connect with a remote server, but there may be additional dependencies.

In order for the remote server to connect with another peer (i.e. a browser) without any additional dependencies you will need to allow inbound/outbound UDP traffic on ports 1024-65535 ([source](https://github.com/aiortc/aiortc/issues/490#issuecomment-788807118)).

If you only have a subset of those UDP ports available, you can use the `--media-ports` flag to specify a comma delimited list of ports to use:

```bash
python server/app.py --workspace <COMFY_WORKSPACE> --media-ports 1024,1025,...
```

If you are running the server in a restrictive network environment where this is not possible, you will need to use a TURN server.

At the moment, the server supports using Twilio's TURN servers (although it is easy to make the update to support arbitrary TURN servers):

1. Sign up for a [Twilio](https://www.twilio.com/en-us) account.
2. Copy the Account SID and Auth Token from [https://console.twilio.com/](https://console.twilio.com/).
3. Set the `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` environment variables.

```bash
export TWILIO_ACCOUNT_SID=...
export TWILIO_AUTH_TOKEN=...
```

## Run UI

**Prerequisities**

- [Node.js](https://nodejs.org/en/download/package-manager)

Install dependencies

```bash
cd ui
npm install --legacy-peer-deps
npm install --save-dev cross-env
```

Run local dev server:

```bash
npm run dev
```

By default the app will be available at <http://localhost:3000>.

The Stream URL is the URL of the [server](#run-server) which defaults to <http://127.0.0.1:8889>.

> [!NOTE]
> To run the UI on HTTPS (necessary for webcam functionality), use `npm run dev:https`. You'll need to accept the self-signed certificate in your browser.

## Limitations

At the moment, a workflow must fufill the following requirements:

- The workflow must have a single primary input node that will receive individual video frames
  - The primary input node is designed by one of the following:
    - A single [PrimaryInputLoadImage](./nodes/video_stream_utils/primary_input_load_image.py) node (see [this workflow](./workflows/liveportait.json) for example usage)
      - This node can be used as a drop-in replacement for a LoadImage node
      - In this scenario, any number of additional LoadImage nodes can be used
    - A single LoadImage node
      - In this scenario, the workflow can only contain the single LoadImage node
  - At runtime, this node is replaced with a LoadTensor node
- The workflow must have a single output using a PreviewImage or SaveImage node
  - At runtime, this node is replaced with a SaveTensor node

## Troubleshoot

This project has been tested locally successfully with the following setup:

- OS: Ubuntu
- GPU: Nvidia RTX 4090
- Driver: 550.127.05
- CUDA: 12.5
- torch: 2.5.1+cu121
