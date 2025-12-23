# Quick Reference: Model Configuration

## Single File vs Directory Download

### Single File (Default)
```yaml
my-model:
  name: "My Model"
  url: "https://huggingface.co/user/repo/resolve/main/file.safetensors"
  path: "loras/model.safetensors"
```

### Directory (Add `is_directory: true`)
```yaml
my-directory:
  name: "My Directory"
  url: "https://huggingface.co/user/repo/tree/main/folder"
  path: "models/folder"
  is_directory: true  # ← Add this!
```

## URL Patterns

| Download Type | URL Pattern | Example |
|---------------|-------------|---------|
| **Single File** | `/resolve/` | `https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter_sd15.safetensors` |
| **Directory** | `/tree/` | `https://huggingface.co/h94/IP-Adapter/tree/main/models/image_encoder` |

## Common Model Paths

| Model Type | Path Pattern |
|------------|--------------|
| Checkpoints | `checkpoints/SD1.5/` |
| LoRAs | `loras/SD1.5/` |
| ControlNet | `controlnet/` |
| VAE | `vae/` or `vae_approx/` |
| IP-Adapter | `ipadapter/` |
| Text Encoders | `text_encoders/CLIPText/` |
| TensorRT/ONNX | `tensorrt/` |

## IP-Adapter Example

```yaml
models:
  # Single file - IP-Adapter model
  ip-adapter-sd15:
    name: "IP Adapter SD15"
    url: "https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter_sd15.safetensors"
    path: "ipadapter/ip-adapter_sd15.safetensors"

  # Directory - CLIP image encoder
  clip-image-encoder:
    name: "CLIP Image Encoder"
    url: "https://huggingface.co/h94/IP-Adapter/tree/main/models/image_encoder"
    path: "ipadapter/models/image_encoder"
    is_directory: true
```

## Usage

```bash
# Use a config
python src/comfystream/scripts/setup_models.py --config my-config.yaml

# Use default config (models.yaml)
python src/comfystream/scripts/setup_models.py
```

## See Also

- [DIRECTORY_DOWNLOADS.md](../DIRECTORY_DOWNLOADS.md) - Detailed directory download guide
- [models-ipadapter-example.yaml](models-ipadapter-example.yaml) - Complete working example
- [README.md](README.md) - Full configuration reference

