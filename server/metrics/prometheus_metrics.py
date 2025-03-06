"""Prometheus metrics utilities."""

from prometheus_client import Gauge, generate_latest
from aiohttp import web
from typing import Optional


class MetricsManager:
    """Manages Prometheus metrics collection."""

    def __init__(self, include_stream_id: bool = False):
        """Initializes the MetricsManager class.

        Args:
            include_stream_id: Whether to include the stream ID as a label in the metrics.
        """
        self._enabled = False
        self._include_stream_id = include_stream_id

        base_labels = ["stream_id"] if include_stream_id else []
        self._fps_gauge = Gauge(
            "stream_fps", "Frames per second of the stream", base_labels
        )

    def enable(self):
        """Enable Prometheus metrics collection."""
        self._enabled = True

    def update_fps_metrics(self, fps: float, stream_id: Optional[str] = None):
        """Update Prometheus metrics for a given stream.

        Args:
            fps: The current frames per second.
            stream_id: The ID of the stream.
        """
        if self._enabled:
            if self._include_stream_id:
                self._fps_gauge.labels(stream_id=stream_id or "").set(fps)
            else:
                self._fps_gauge.set(fps)

    async def metrics_handler(self, _):
        """Handle Prometheus metrics endpoint."""
        return web.Response(body=generate_latest(), content_type="text/plain")
