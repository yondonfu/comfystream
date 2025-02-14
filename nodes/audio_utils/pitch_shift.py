import numpy as np
import librosa

class PitchShifter:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ("WAVEFORM", "INT")
    FUNCTION = "execute"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("WAVEFORM",),
                "sample_rate": ("INT",),
                "pitch_shift": ("FLOAT", {
                    "default": 4.0, 
                    "min": 0.0, 
                    "max": 12.0, 
                    "step": 0.5
                }),
            }
        }

    @classmethod
    def IS_CHANGED(cls):
        return float("nan")

    def execute(self, audio, sample_rate, pitch_shift):
        audio_float = audio.astype(np.float32) / 32768.0
        shifted_audio = librosa.effects.pitch_shift(y=audio_float, sr=sample_rate, n_steps=pitch_shift)
        shifted_int16 = np.clip(shifted_audio * 32768.0, -32768, 32767).astype(np.int16)
        return shifted_int16, sample_rate
