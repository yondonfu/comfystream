# borrowed from Acly's comfyui-tooling-nodes
# https://github.com/Acly/comfyui-tooling-nodes/blob/main/nodes.py

# TODO: I think we can send tensor data directly to the pipeline in the websocket response.
#       Worth talking to ComfyAnonymous about this.

import numpy as np
from PIL import Image
from server import PromptServer, BinaryEventTypes

class SendImageWebsocket:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "format": (["PNG", "JPEG"], {"default": "PNG"}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "send_images"
    OUTPUT_NODE = True
    CATEGORY = "external_tooling"

    def send_images(self, images, format):
        results = []
        for tensor in images:
            array = 255.0 * tensor.cpu().numpy()
            image = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))

            server = PromptServer.instance
            server.send_sync(
                BinaryEventTypes.UNENCODED_PREVIEW_IMAGE,
                [format, image, None],
                server.client_id,
            )
            results.append({
                "source": "websocket",
                "content-type": f"image/{format.lower()}",
                "type": "output",
            })

        return {"ui": {"images": results}}