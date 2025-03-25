from comfystream import tensor_cache


class LoadTensor:
    CATEGORY = "tensor_utils"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "execute"

    @classmethod
    def INPUT_TYPES(s):
        return {}

    @classmethod
    def IS_CHANGED():
        return float("nan")

    def execute(self):
        frame = tensor_cache.image_inputs.get(block=True)
        frame.side_data.skipped = False
        return (frame.side_data.processed_input,)
