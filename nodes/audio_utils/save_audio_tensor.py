from comfystream import tensor_cache

class SaveAudioTensor:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True


    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("WAVEFORM",)
            }
        }

    @classmethod
    def IS_CHANGED(s):
        return float("nan")

    def execute(self, audio):
        tensor_cache.audio_outputs.put_nowait(audio)
        return (audio,)

