# borrowed from Acly's comfyui-tooling-nodes
# https://github.com/Acly/comfyui-tooling-nodes/blob/main/nodes.py

# TODO: I think we can recieve tensor data directly from the pipeline through the /prompt endpoint as JSON
#       This may be more efficient than sending base64 encoded images through the websocket and
#       allow for alternative data formats.

from PIL import Image
import base64
import numpy as np
import torch
from io import BytesIO

class LoadImageBase64:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"image": ("STRING", {"multiline": False})}}

    RETURN_TYPES = ("IMAGE", "MASK")
    CATEGORY = "external_tooling"
    FUNCTION = "load_image"

    def load_image(self, image):
        imgdata = base64.b64decode(image)
        img = Image.open(BytesIO(imgdata))

        if "A" in img.getbands():
            mask = np.array(img.getchannel("A")).astype(np.float32) / 255.0
            mask = torch.from_numpy(mask)
        else:
            mask = None

        img = img.convert("RGB")
        img = np.array(img).astype(np.float32) / 255.0
        img = torch.from_numpy(img)[None,]

        return (img, mask)