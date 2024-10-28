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
        input = tensor_cache.inputs.pop()
        return (input,)
