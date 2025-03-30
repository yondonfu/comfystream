"""Module for tracking real-time statistics of individual media tracks."""

from typing import Any, Dict, Optional
from utils.fps_meter import FPSMeter
from .prometheus_metrics import MetricsManager
from .pipeline_stats import PipelineStats
import time


class TrackStats:
    """Tracks real-time statistics for an individual media track.

    Attributes:
        fps_meter: The FPSMeter instance for tracking frame rate.
        start_timestamp: The timestamp when the track started.
        pipeline: The PipelineStats instance for tracking pipeline-related metrics.
    """

    def __init__(
        self,
        track_id: str,
        track_kind: str,
        metrics_manager: Optional[MetricsManager] = None,
    ):
        """Initializes the TrackStats class.

        Args:
            track_id: The unique identifier for the media track.
            track_kind: The kind of the track (e.g., "video" or "audio").
            metrics_manager: An optional Prometheus metrics manager instance for
                updating metrics related to the track.
        """
        update_metrics_callback = (
            metrics_manager.update_fps if metrics_manager else None
        )
        self.fps_meter = FPSMeter(
            track_id=track_id,
            track_kind=track_kind,
            update_metrics_callback=update_metrics_callback,
        )
        self.pipeline = PipelineStats(
            metrics_manager=metrics_manager, track_id=track_id
        )

        self.start_timestamp = None

        self._track_id = track_id
        self._track_kind = track_kind
        self._metrics_manager = metrics_manager
        self._startup_time = None

    @property
    def startup_time(self) -> float:
        """Time taken to start the track."""
        return self._startup_time

    @startup_time.setter
    def startup_time(self, value: float):
        """Sets the time taken to start the track.

        Updates the Prometheus metrics if a metrics manager is available.
        """
        if self._metrics_manager:
            self._metrics_manager.update_startup_time(
                value, self._track_id, self._track_kind
            )
        self._startup_time = value

    async def get_fps(self) -> float:
        """Current frames per second (FPS) of the track.

        Alias for the FPSMeter's `get_fps` method.
        """
        return await self.fps_meter.get_fps()

    async def get_fps_measurements(self) -> list:
        """List of FPS measurements over time for the track.

        Alias for the FPSMeter's `get_fps_measurements` method.
        """
        return await self.fps_meter.get_fps_measurements()

    async def get_average_fps(self) -> float:
        """Average FPS over the last minute for the track.

        Alias for the FPSMeter's `get_average_fps` method.
        """
        return await self.fps_meter.get_average_fps()

    async def get_last_fps_calculation_time(self) -> float:
        """Timestamp of the last FPS calculation for the track.

        Alias for the FPSMeter's `get_last_fps_calculation_time` method.
        """
        return await self.fps_meter.get_last_fps_calculation_time()

    @property
    def time(self) -> float:
        """Elapsed time since the track started."""
        return (
            0.0
            if self.start_timestamp is None
            else time.monotonic() - self.start_timestamp
        )

    async def to_dict(self) -> Dict[str, Any]:
        """Converts track statistics to a dictionary for JSON serialization.

        Returns:
            A dictionary containing satistics about the media track.
        """
        pipeline_stats = {
            "warmup": getattr(self.pipeline, f"{self._track_kind}_warmup_time", None)
        }
        return {
            "type": self._track_kind,
            "timestamp": self.time,
            "startup_time": self.startup_time,
            "pipeline": pipeline_stats,
            "fps": await self.get_fps(),
            "minute_avg_fps": await self.get_average_fps(),
            "minute_fps_array": await self.get_fps_measurements(),
        }
