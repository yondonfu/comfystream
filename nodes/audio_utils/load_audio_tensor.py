import numpy as np

from comfystream import tensor_cache

class LoadAudioTensor:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "execute"

    def __init__(self):
        self.audio_buffer = np.array([], dtype=np.int16)
        self.buffer_samples = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "buffer_size": ("FLOAT", {"default": 500.0}),
                "sample_rate": ("INT", {"default": 48000})
            }
        }

    @classmethod
    def IS_CHANGED():
        return float("nan")

    def execute(self, buffer_size, sample_rate):
        if not self.buffer_samples:
            self.buffer_samples = int(buffer_size * sample_rate / 1000)

        while self.audio_buffer.size < self.buffer_samples:
            audio = tensor_cache.audio_inputs.get()
            self.audio_buffer = np.concatenate((self.audio_buffer, audio))

        buffered_audio = self.audio_buffer
        self.audio_buffer = np.array([], dtype=np.int16)
        return (buffered_audio,)
