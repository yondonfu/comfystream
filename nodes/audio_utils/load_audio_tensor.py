import numpy as np
import torch

from comfystream import tensor_cache

class LoadAudioTensor:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "execute"
    
    def __init__(self):
        self.audio_buffer = np.empty(0, dtype=np.int16)
        self.buffer_samples = None
        self.sample_rate = None
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "buffer_size": ("FLOAT", {"default": 500.0}),
            }
        }
    
    @classmethod
    def IS_CHANGED(**kwargs):
        return float("nan")
    
    def execute(self, buffer_size):
        if self.sample_rate is None or self.buffer_samples is None:
            frame = tensor_cache.audio_inputs.get(block=True)
            self.sample_rate = frame.sample_rate
            self.buffer_samples = int(self.sample_rate * buffer_size / 1000)
            self.leftover = frame.side_data.input
        
        if self.leftover.shape[0] < self.buffer_samples:
            chunks = [self.leftover] if self.leftover.size > 0 else []
            total_samples = self.leftover.shape[0]
            
            while total_samples < self.buffer_samples:
                frame = tensor_cache.audio_inputs.get(block=True)
                if frame.sample_rate != self.sample_rate:
                    raise ValueError("Sample rate mismatch")
                chunks.append(frame.side_data.input)
                total_samples += frame.side_data.input.shape[0]
            
            merged_audio = np.concatenate(chunks, dtype=np.int16)
            buffered_audio = merged_audio[:self.buffer_samples]
            self.leftover = merged_audio[self.buffer_samples:]
        else:
            buffered_audio = self.leftover[:self.buffer_samples]
            self.leftover = self.leftover[self.buffer_samples:]
                
        # Convert numpy array to torch tensor and normalize int16 to float32
        waveform_tensor = torch.from_numpy(buffered_audio.astype(np.float32) / 32768.0)
        
        # Ensure proper tensor shape: (batch, channels, samples)
        if waveform_tensor.dim() == 1:
            # Mono: (samples,) -> (1, 1, samples)
            waveform_tensor = waveform_tensor.unsqueeze(0).unsqueeze(0)
        elif waveform_tensor.dim() == 2:
            # Assume (channels, samples) and add batch dimension
            waveform_tensor = waveform_tensor.unsqueeze(0)
        
        # Return AUDIO dictionary format
        audio_dict = {
            "waveform": waveform_tensor,
            "sample_rate": self.sample_rate
        }
        
        return (audio_dict,)
