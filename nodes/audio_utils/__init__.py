from .apply_whisper import ApplyWhisper
from .load_audio_tensor import LoadAudioTensor
from .save_asr_response import SaveASRResponse

NODE_CLASS_MAPPINGS = {"LoadAudioTensor": LoadAudioTensor, "SaveASRResponse": SaveASRResponse, "ApplyWhisper": ApplyWhisper}

__all__ = ["NODE_CLASS_MAPPINGS"]
