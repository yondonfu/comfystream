"""Prometheus metrics utilities."""

from prometheus_client import Gauge, generate_latest
from aiohttp import web


class MetricsManager:
    """Manages Prometheus metrics collection."""

    def __init__(self):
        self._enabled = False
        self._fps_gauge = Gauge(
            "stream_fps", "Frames per second of the stream", ["stream_id"]
        )

    def enable(self):
        """Enable Prometheus metrics collection."""
        self._enabled = True

    def update_metrics(self, stream_id: str, fps: float):
        """Update Prometheus metrics for a given stream.

        Args:
            stream_id: The ID of the stream.
            fps: The current frames per second.
            avg_fps: The average frames per second per minute.
        """
        if self._enabled:
            self._fps_gauge.labels(stream_id=stream_id).set(fps)

    async def metrics_handler(self, _):
        """Handle Prometheus metrics endpoint."""
        return web.Response(body=generate_latest(), content_type="text/plain")
