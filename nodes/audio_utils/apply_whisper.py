import torch
import whisper

class ApplyWhisper:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO",),
                "model": (["base", "tiny", "small", "medium", "large"],),
            }
        }

    CATEGORY = "audio_utils"
    RETURN_TYPES = ("DICT",)
    FUNCTION = "apply_whisper"

    def __init__(self):
        self.model = None
        self.audio_buffer = []
        # TO:DO to get them as params
        self.sample_rate = 16000
        self.min_duration = 1.0

    def apply_whisper(self, audio, model):
        if self.model is None:
            self.model = whisper.load_model(model).cuda()

        self.audio_buffer.append(audio)
        total_duration = sum(chunk.shape[0] / self.sample_rate for chunk in self.audio_buffer)
        if total_duration < self.min_duration:
            return {"text": "", "segments_alignment": [], "words_alignment": []}

        concatenated_audio = torch.cat(self.audio_buffer, dim=0).cuda()
        self.audio_buffer = []
        result = self.model.transcribe(concatenated_audio.float(), fp16=True, word_timestamps=True)
        segments = result["segments"]
        segments_alignment = []
        words_alignment = []

        for segment in segments:
            segment_dict = {
                "value": segment["text"].strip(),
                "start": segment["start"],
                "end": segment["end"]
            }
            segments_alignment.append(segment_dict)

            for word in segment["words"]:
                word_dict = {
                    "value": word["word"].strip(),
                    "start": word["start"],
                    "end": word["end"]
                }
                words_alignment.append(word_dict)

        return ({
            "text": result["text"].strip(),
            "segments_alignment": segments_alignment,
            "words_alignment": words_alignment
        },)
