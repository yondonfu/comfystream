"""Utility functions for the server."""
import asyncio
import random
import types
import logging
import json
from aiohttp import web
from aiortc import MediaStreamTrack
from typing import List, Tuple, Any, Dict

logger = logging.getLogger(__name__)


# Original issue: https://github.com/aiortc/aioice/pull/63
# Copied from: https://github.com/toverainc/willow-inference-server/pull/17/files
def patch_loop_datagram(local_ports: List[int]):
    loop = asyncio.get_event_loop()
    if getattr(loop, "_patch_done", False):
        return

    # Monkey patch aiortc to control ephemeral ports
    old_create_datagram_endpoint = loop.create_datagram_endpoint

    async def create_datagram_endpoint(
        self, protocol_factory, local_addr: Tuple[str, int] = None, **kwargs
    ):
        # if port is specified just use it
        if local_addr and local_addr[1]:
            return await old_create_datagram_endpoint(
                protocol_factory, local_addr=local_addr, **kwargs
            )
        if local_addr is None:
            return await old_create_datagram_endpoint(
                protocol_factory, local_addr=None, **kwargs
            )
        # if port is not specified make it use our range
        ports = list(local_ports)
        random.shuffle(ports)
        for port in ports:
            try:
                ret = await old_create_datagram_endpoint(
                    protocol_factory, local_addr=(local_addr[0], port), **kwargs
                )
                logger.debug(f"create_datagram_endpoint chose port {port}")
                return ret
            except OSError as exc:
                if port == ports[-1]:
                    # this was the last port, give up
                    raise exc
        raise ValueError("local_ports must not be empty")

    loop.create_datagram_endpoint = types.MethodType(create_datagram_endpoint, loop)
    loop._patch_done = True


def add_prefix_to_app_routes(app: web.Application, prefix: str):
    """Add a prefix to all routes in the given application.

    Args:
        app: The web application whose routes will be prefixed.
        prefix: The prefix to add to all routes.
    """
    prefix = prefix.rstrip("/")
    for route in list(app.router.routes()):
        new_path = prefix + route.resource.canonical
        app.router.add_route(route.method, new_path, route.handler)


class StreamStats:
    """Handles real-time video stream statistics collection."""

    def __init__(self, app: web.Application):
        """Initializes the StreamMetrics class.

        Args:
            app: The web application instance storing video streams under the
                "video_tracks" key.
        """
        self._app = app

    async def collect_video_metrics(self, video_track: MediaStreamTrack) -> Dict[str, Any]:
        """Collects real-time statistics for a video track.

        Args:
            video_track: The video stream track instance.

        Returns:
            A dictionary containing FPS-related statistics.
        """
        return {
            "timestamp": await video_track.last_fps_calculation_time,
            "fps": await video_track.fps,
            "minute_avg_fps": await video_track.average_fps,
            "minute_fps_array": await video_track.fps_measurements,
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
        video_track = self._app["video_tracks"].get(stream_id)

        if video_track:
            stats = await self.collect_video_metrics(video_track)
        else:
            stats = {"error": "Stream not found"}

        return web.Response(
            content_type="application/json",
            text=json.dumps(stats),
        )
