import numpy as np
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
                "audio": ("AUDIO",)
            }
        }

    @classmethod
    def IS_CHANGED(s):
        return float("nan")

    def execute(self, audio):
        # Extract waveform tensor from AUDIO format
        waveform = audio["waveform"]
        
        # Convert to numpy and flatten for pipeline compatibility
        if hasattr(waveform, 'cpu'):
            # PyTorch tensor
            waveform_numpy = waveform.squeeze().cpu().numpy()
        else:
            # Already numpy
            waveform_numpy = waveform.squeeze()
        
        # Ensure 1D array for pipeline buffer concatenation
        if waveform_numpy.ndim > 1:
            waveform_numpy = waveform_numpy.flatten()
        
        # Convert to int16 if needed (pipeline expects int16)
        if waveform_numpy.dtype == np.float32:
            waveform_numpy = (waveform_numpy * 32767).astype(np.int16)
        elif waveform_numpy.dtype != np.int16:
            waveform_numpy = waveform_numpy.astype(np.int16)
        
        tensor_cache.audio_outputs.put_nowait(waveform_numpy)
        return (audio,)
