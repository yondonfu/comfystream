from comfystream import tensor_cache

class LoadAudioTensor:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "execute"

    @classmethod
    def INPUT_TYPES(s):
        return {}

    @classmethod
    def IS_CHANGED():
        return float("nan")

    def execute(self):
        audio = tensor_cache.inputs.pop()
        return (audio,)