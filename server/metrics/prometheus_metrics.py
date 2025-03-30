"""Module for handling Prometheus metrics for media tracks."""

from prometheus_client import Gauge, generate_latest
from aiohttp import web
from typing import Optional


class MetricsManager:
    """Manages Prometheus metrics collection for media tracks."""

    def __init__(
        self, include_track_id: bool = False, include_track_kind: bool = False
    ):
        """Initializes the MetricsManager class.

        Args:
            include_track_id: Whether to include the track ID as a label.
            include_track_kind: Whether to include the track kind as a label.
        """
        self._enabled = False
        self._include_track_id = include_track_id
        self._include_track_kind = include_track_kind

        base_labels = []
        if include_track_id:
            base_labels.append("track_id")
        if include_track_kind:
            base_labels.append("track_kind")

        self._gauges = {
            "fps": Gauge(
                "stream_fps",
                "Frames per second for the stream. Defaults to all tracks; specific "
                "tracks when labels are applied.",
                base_labels,
            ),
            "startup_time": Gauge(
                "stream_startup_time",
                "Startup time for the stream. Defaults to all tracks; specific tracks "
                "when labels are applied.",
                base_labels,
            ),
            "warmup_time": Gauge(
                "stream_warmup_time",
                "Warmup time for the stream pipeline. Defaults to all tracks; specific "
                "tracks when labels are applied.",
                base_labels,
            ),
        }

    def _set_gauge(
        self,
        gauge: Gauge,
        value: float,
        track_id: Optional[str] = None,
        track_kind: Optional[str] = None,
    ):
        """Set the value of a gauge metric with dynamic labels.

        Args:
            gauge: The Prometheus gauge to update.
            value: The value to set for the gauge.
            track_id: The ID of the track.
        """
        if not self._enabled:
            return

        labels = {}
        if self._include_track_id and track_id:
            labels["track_id"] = track_id
        if self._include_track_kind and track_kind:
            labels["track_kind"] = track_kind

        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)

    def enable(self):
        """Enable Prometheus metrics collection."""
        self._enabled = True

    def update_fps(
        self,
        fps: float,
        track_id: Optional[str] = None,
        track_kind: Optional[str] = None,
    ):
        """Update FPS metrics for a given track.

        Args:
            fps: The current frames per second.
            track_id: The ID of the track.
            track_kind: The kind of the track (e.g., "video", "audio").
        """
        self._set_gauge(
            self._gauges["fps"], fps, track_id=track_id, track_kind=track_kind
        )

    def update_startup_time(
        self,
        startup_time: float,
        track_id: Optional[str] = None,
        track_kind: Optional[str] = None,
    ):
        """Update startup time metrics for a given track.

        Args:
            startup_time: The time taken to start the track.
            track_id: The ID of the track.
            track_kind: The kind of the track (e.g., "video", "audio").
        """
        self._set_gauge(
            self._gauges["startup_time"],
            startup_time,
            track_id=track_id,
            track_kind=track_kind,
        )

    def update_warmup_time(
        self,
        warmup_time: float,
        track_id: Optional[str] = None,
        track_kind: Optional[str] = None,
    ):
        """Update warmup time metrics for a given track.

        Args:
            warmup_time: The time taken to warm up the track.
            track_id: The ID of the track.
            track_kind: The kind of the track (e.g., "video", "audio").
        """
        self._set_gauge(
            self._gauges["warmup_time"],
            warmup_time,
            track_id=track_id,
            track_kind=track_kind,
        )

    async def metrics_handler(self, _):
        """Handle Prometheus metrics endpoint."""
        return web.Response(body=generate_latest(), content_type="text/plain")
