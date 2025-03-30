"""Module for handling real-time media track statistics for JSON API publishing."""

from typing import Any, Dict
import json
from aiohttp import web
from aiortc import MediaStreamTrack


class StreamStatsManager:
    """Handles real-time statistics collection for media tracks.
    
    Note:
        This class currently uses `track_id` to identify individual media tracks
        (e.g., video or audio) instead of `stream_id`. In the future, this may
        be extended to support stream-level statistics where a `stream_id` can
        represent multiple tracks (e.g., video and audio tracks for the same stream).
    """

    def __init__(self, app: web.Application):
        """Initializes the StreamStatsManager class.

        Args:
            app: The web application instance storing media tracks.
        """
        self._app = app

    async def collect_video_stats(
        self, video_track: MediaStreamTrack
    ) -> Dict[str, Any]:
        """Collects real-time statistics for a video track.

        Args:
            video_track: The video track instance.

        Returns:
            A dictionary containing FPS-related statistics for the video track.
        """
        return await video_track.stats.to_dict()

    async def collect_audio_stats(
        self, audio_track: MediaStreamTrack
    ) -> Dict[str, Any]:
        """Collects real-time statistics for an audio track.

        Args:
            audio_track: The audio track instance.

        Returns:
            A dictionary containing FPS-related statistics for the audio track.
        """
        return await audio_track.stats.to_dict()

    async def collect_all_stream_stats(self, _) -> web.Response:
        """Retrieves real-time statistics for all active video and audio tracks.

        Returns:
            A JSON response containing statistics for all tracks.
        """
        tracks = {
            **self._app.get("video_tracks", {}),
            **self._app.get("audio_tracks", {}),
        }
        all_stats = {
            track_id: await (
                self.collect_video_stats(track)
                if track.kind == "video"
                else self.collect_audio_stats(track)
            )
            for track_id, track in tracks.items()
        }

        return web.Response(
            content_type="application/json",
            text=json.dumps(all_stats),
        )

    async def collect_stream_stats_by_id(self, request: web.Request) -> web.Response:
        """Retrieves real-time statistics for a specific video or audio track by ID.

        Args:
            request: The HTTP request containing the track ID.

        Returns:
            A JSON response with track statistics or an error message.
        """
        track_id = request.match_info.get("track_id")
        tracks = {
            **self._app.get("video_tracks", {}),
            **self._app.get("audio_tracks", {}),
        }
        track = tracks.get(track_id)

        if not track:
            error_response = {"error": "Track not found"}
            return web.Response(
                status=404,
                content_type="application/json",
                text=json.dumps(error_response),
            )

        stats = await (
            self.collect_video_stats(track)
            if track.kind == "video"
            else self.collect_audio_stats(track)
        )
        return web.Response(
            content_type="application/json",
            text=json.dumps(stats),
        )
