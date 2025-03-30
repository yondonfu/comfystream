"""Module for handling real-time media pipeline statistics."""

from typing import Optional, Dict, Any
from .prometheus_metrics import MetricsManager


class PipelineStats:
    """Tracks real-time statistics of the media pipeline.

    Attributes:
        metrics_manager: The Prometheus metrics manager instance.
        track_id: The ID of the associated media track.
    """

    def __init__(
        self,
        metrics_manager: Optional[MetricsManager] = None,
        track_id: Optional[str] = None,
    ):
        """Initializes the PipelineStats class.

        Args:
            metrics_manager: The Prometheus metrics manager instance.
            track_id: The ID of the associated media track.
        """
        self.metrics_manager = metrics_manager
        self.track_id = track_id

        self._video_warmup_time = None
        self._audio_warmup_time = None

    @property
    def video_warmup_time(self) -> float:
        """Time taken to warm up the video pipeline."""
        return self._video_warmup_time

    @video_warmup_time.setter
    def video_warmup_time(self, value: float):
        """Sets the time taken to warm up the video pipeline."""
        self._video_warmup_time = value
        if self.metrics_manager:
            self.metrics_manager.update_warmup_time(value, self.track_id)

    @property
    def audio_warmup_time(self) -> float:
        """Time taken to warm up the audio pipeline."""
        return self._audio_warmup_time

    @audio_warmup_time.setter
    def audio_warmup_time(self, value: float):
        """Sets the time taken to warm up the audio pipeline."""
        self._audio_warmup_time = value
        if self.metrics_manager:
            self.metrics_manager.update_warmup_time(value, self.track_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to a dictionary for easy JSON serialization."""
        return {
            "video_warmup_time": self._video_warmup_time,
            "audio_warmup_time": self._audio_warmup_time,
        }
