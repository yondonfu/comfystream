from comfystream import tensor_cache

class SaveASRResponse:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "data": ("DICT",),
            }
        }

    @classmethod
    def IS_CHANGED(s):
        return float("nan")

    def execute(self, data: dict):
        fut = tensor_cache.outputs.pop()
        fut.set_result(data)
        return data