from comfystream import tensor_cache

class SaveAudioTensor:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True

    def __init__(self):
        self.frame_samples = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO",),
                "frame_size": ("FLOAT", {"default": 20.0}),
                "sample_rate": ("INT", {"default": 48000})
            }
        }

    @classmethod
    def IS_CHANGED(s):
        return float("nan")

    def execute(self, audio, frame_size, sample_rate):
        if self.frame_samples is None:
            self.frame_samples = int(frame_size * sample_rate / 1000)
            
        for idx in range(0, len(audio), self.frame_samples):
            frame = audio[idx:idx + self.frame_samples]
            fut = tensor_cache.audio_outputs.get()
            fut.set_result(frame)
        return (audio,)

