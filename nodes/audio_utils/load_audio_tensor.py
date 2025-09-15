import numpy as np

from comfystream import tensor_cache

class LoadAudioTensor:
    CATEGORY = "audio_utils"
    RETURN_TYPES = ("WAVEFORM", "INT")
    RETURN_NAMES = ("audio", "sample_rate")
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
    def IS_CHANGED():
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
                
        return buffered_audio, self.sample_rate
