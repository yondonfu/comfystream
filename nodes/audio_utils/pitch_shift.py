import numpy as np
import librosa
import torch

class PitchShifter:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "execute"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
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

    def execute(self, audio, pitch_shift):
        # Extract waveform and sample rate from AUDIO format
        waveform = audio["waveform"]
        sample_rate = audio["sample_rate"]
        
        # Convert tensor to numpy and ensure proper format for librosa
        if isinstance(waveform, torch.Tensor):
            audio_numpy = waveform.squeeze().cpu().numpy()
        else:
            audio_numpy = waveform.squeeze()
        
        # Ensure float32 format and proper normalization for librosa processing
        if audio_numpy.dtype != np.float32:
            audio_numpy = audio_numpy.astype(np.float32)
        
        # Check if data needs normalization (librosa expects [-1, 1] range)
        max_abs_val = np.abs(audio_numpy).max()
        if max_abs_val > 1.0:
            # Data appears to be in int16 range, normalize it
            audio_numpy = audio_numpy / 32768.0
        
        # Apply pitch shift
        shifted_audio = librosa.effects.pitch_shift(y=audio_numpy, sr=sample_rate, n_steps=pitch_shift)
        
        # Convert back to tensor and restore original shape
        shifted_tensor = torch.from_numpy(shifted_audio).float()
        if waveform.dim() == 3:  # (batch, channels, samples)
            shifted_tensor = shifted_tensor.unsqueeze(0).unsqueeze(0)
        elif waveform.dim() == 2:  # (channels, samples) 
            shifted_tensor = shifted_tensor.unsqueeze(0)
        
        # Return AUDIO format
        result_audio = {
            "waveform": shifted_tensor,
            "sample_rate": sample_rate
        }
        
        return (result_audio,)
