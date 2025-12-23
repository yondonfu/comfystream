# ComfyStream Docker Build Configuration

This folder contains the Docker files that can be used to run ComfyStream in a containerized fashion or to work on the codebase within a dev container. This README contains the general usage instructions while the [Devcontainer Readme](../.devcontainer/README.md) contains instructions on how to use Comfystream inside a dev container and get quickly started with your development journey.

## Containers

- [Dockerfile](Dockerfile) - The main Dockerfile that can be used to run ComfyStream in a containerized fashion.
- [Dockerfile.base](Dockerfile.base) - The base Dockerfile that can be used to build the base image for ComfyStream.

## Building with Custom Nodes Configuration

The base Docker image supports specifying a custom nodes configuration file during build time using the `NODES_CONFIG` build argument.

### Usage

#### Default build (uses `nodes.yaml`)
```bash
docker build -t livepeer/comfyui-base -f docker/Dockerfile .
```

#### Build with custom config from configs directory
```bash
docker build -f docker/Dockerfile.base \
  --build-arg NODES_CONFIG=nodes-streamdiffusion.yaml \
  -t comfyui-base:streamdiffusion .
```

#### Build with config from absolute path
```bash
docker build -f docker/Dockerfile.base \
  --build-arg NODES_CONFIG=/path/to/custom-nodes.yaml \
  -t comfyui-base:custom .
```

### Available Build Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `BASE_IMAGE` | `nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04` | Base CUDA image |
| `CONDA_VERSION` | `latest` | Miniconda version |
| `PYTHON_VERSION` | `3.12` | Python version |
| `NODES_CONFIG` | `nodes.yaml` | Nodes configuration file (filename or path) |
| `CACHEBUST` | `static` | Cache invalidation for node setup |

### Configuration Files in configs/

- **`nodes.yaml`** - Full node configuration (default)
- **`nodes-streamdiffusion.yaml`** - Minimal set of nodes for faster builds

### Examples

### Build the Main Image

To build the main image, run the following command:

```bash
docker build -t livepeer/comfystream -f docker/Dockerfile .
```

### Run the Container

To start the container in interactive mode, run the following command:

```bash
docker run -it --gpus all livepeer/comfystream
```

To start the Comfystream server, run the following command:

```bash
docker run --gpus all livepeer/comfystream --server
```

There are multiple options that can be passed to the Comfystream server. To see the list of available options, run the following command:

```bash
docker run --gpus all livepeer/comfystream --help
```
