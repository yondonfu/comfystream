import numpy as np
import torch
import queue
from comfystream import tensor_cache
from comfystream.exceptions import ComfyStreamInputTimeoutError, ComfyStreamAudioBufferError


class LoadAudioTensor:
    CATEGORY = "ComfyStream/Loaders"
    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "execute"
    DESCRIPTION = "Load audio tensor from ComfyStream input with timeout."
    
    def __init__(self):
        self.audio_buffer = np.empty(0, dtype=np.int16)
        self.buffer_samples = None
        self.sample_rate = None
        self.leftover = np.empty(0, dtype=np.int16)
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "buffer_size": ("FLOAT", {
                    "default": 500.0,
                    "tooltip": "Audio buffer size in milliseconds"
                }),
            },
            "optional": {
                "timeout_seconds": ("FLOAT", {
                    "default": 1.0, 
                    "min": 0.1, 
                    "max": 30.0, 
                    "step": 0.1,
                    "tooltip": "Timeout in seconds"
                }),
            }
        }
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def execute(self, buffer_size: float, timeout_seconds: float = 1.0):
        # Initialize if needed
        if self.sample_rate is None or self.buffer_samples is None:
            try:
                frame = tensor_cache.audio_inputs.get(block=True, timeout=timeout_seconds)
                self.sample_rate = frame.sample_rate
                self.buffer_samples = int(self.sample_rate * buffer_size / 1000)
                self.leftover = frame.side_data.input
            except queue.Empty:
                raise ComfyStreamInputTimeoutError("audio", timeout_seconds)
        
        # Use leftover data if available
        if self.leftover.shape[0] >= self.buffer_samples:
            buffered_audio = self.leftover[:self.buffer_samples]
            self.leftover = self.leftover[self.buffer_samples:]
        else:
            # Collect more audio chunks
            chunks = [self.leftover] if self.leftover.size > 0 else []
            total_samples = self.leftover.shape[0]
            
            while total_samples < self.buffer_samples:
                try:
                    frame = tensor_cache.audio_inputs.get(block=True, timeout=timeout_seconds)
                    if frame.sample_rate != self.sample_rate:
                        raise ValueError(f"Sample rate mismatch: expected {self.sample_rate}Hz, got {frame.sample_rate}Hz")
                    chunks.append(frame.side_data.input)
                    total_samples += frame.side_data.input.shape[0]
                except queue.Empty:
                    raise ComfyStreamAudioBufferError(timeout_seconds, self.buffer_samples, total_samples)
            
            merged_audio = np.concatenate(chunks, dtype=np.int16)
            buffered_audio = merged_audio[:self.buffer_samples]
            self.leftover = merged_audio[self.buffer_samples:] if merged_audio.shape[0] > self.buffer_samples else np.empty(0, dtype=np.int16)
                
        # Convert to ComfyUI AUDIO format
        waveform_tensor = torch.from_numpy(buffered_audio.astype(np.float32) / 32768.0)
        
        # Ensure proper tensor shape: (batch, channels, samples)
        if waveform_tensor.dim() == 1:
            waveform_tensor = waveform_tensor.unsqueeze(0).unsqueeze(0)
        elif waveform_tensor.dim() == 2:
            waveform_tensor = waveform_tensor.unsqueeze(0)
        
        return ({"waveform": waveform_tensor, "sample_rate": self.sample_rate},)