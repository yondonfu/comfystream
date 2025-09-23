"""ComfyStream specific exceptions."""


class ComfyStreamInputTimeoutError(Exception):
    """Raised when input tensors are not available within timeout."""
    
    def __init__(self, input_type: str, timeout_seconds: float):
        self.input_type = input_type
        self.timeout_seconds = timeout_seconds
        message = f"No {input_type} frames available after {timeout_seconds}s timeout"
        super().__init__(message)


class ComfyStreamAudioBufferError(ComfyStreamInputTimeoutError):
    """Audio buffer insufficient data error."""
    
    def __init__(self, timeout_seconds: float, needed_samples: int, available_samples: int):
        self.needed_samples = needed_samples
        self.available_samples = available_samples
        super().__init__("audio", timeout_seconds)
