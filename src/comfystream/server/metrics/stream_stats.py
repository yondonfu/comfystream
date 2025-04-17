"""Handles real-time video stream statistics (non-Prometheus, JSON API)."""

from typing import Any, Dict
import json
from aiohttp import web
from aiortc import MediaStreamTrack


class StreamStatsManager:
    """Handles real-time video stream statistics collection."""

    def __init__(self, app: web.Application):
        """Initializes the StreamMetrics class.

        Args:
            app: The web application instance storing stream tracks.
        """
        self._app = app

    async def collect_video_metrics(
        self, video_track: MediaStreamTrack
    ) -> Dict[str, Any]:
        """Collects real-time statistics for a video track.

        Args:
            video_track: The video stream track instance.

        Returns:
            A dictionary containing FPS-related statistics.
        """
        return {
            "timestamp": await video_track.fps_meter.last_fps_calculation_time,
            "fps": await video_track.fps_meter.fps,
            "minute_avg_fps": await video_track.fps_meter.average_fps,
            "minute_fps_array": await video_track.fps_meter.fps_measurements,
        }

    async def collect_all_stream_metrics(self, _) -> web.Response:
        """Retrieves real-time metrics for all active video streams.

        Returns:
            A JSON response containing FPS statistics for all streams.
        """
        video_tracks = self._app.get("video_tracks", {})
        all_stats = {
            stream_id: await self.collect_video_metrics(track)
            for stream_id, track in video_tracks.items()
        }

        return web.Response(
            content_type="application/json",
            text=json.dumps(all_stats),
        )

    async def collect_stream_metrics_by_id(self, request: web.Request) -> web.Response:
        """Retrieves real-time metrics for a specific video stream by ID.

        Args:
            request: The HTTP request containing the stream ID.

        Returns:
            A JSON response with stream metrics or an error message.
        """
        stream_id = request.match_info.get("stream_id")
        video_tracks = self._app.get("video_tracks", {})
        video_track = video_tracks.get(stream_id)

        if video_track:
            stats = await self.collect_video_metrics(video_track)
        else:
            stats = {"error": "Stream not found"}

        return web.Response(
            content_type="application/json",
            text=json.dumps(stats),
        )
