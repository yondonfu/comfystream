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


class StreamStats:
    """Class to get stream statistics."""

    def __init__(self, app: web.Application):
        """Initialize the StreamStats class."""
        self._app = app

    def get_video_track_stats(self, video_track: MediaStreamTrack) -> Dict[str, Any]:
        """Get statistics for a video track.

        Args:
            video_track: The VideoStreamTrack instance.

        Returns:
            A dictionary containing the statistics.
        """
        return {
            "fps": video_track.fps,
        }

    async def get_stats(self, _) -> web.Response:
        """Get the current stream statistics for all streams.

        Args:
            request: The HTTP GET request.

        Returns:
            The HTTP response containing the statistics.
        """
        video_tracks = self._app.get("video_tracks", {})
        all_stats = {
            stream_id: self.get_video_track_stats(track)
            for stream_id, track in video_tracks.items()
        }

        return web.Response(
            content_type="application/json",
            text=json.dumps(all_stats),
        )

    async def get_stats_by_id(self, request: web.Request) -> web.Response:
        """Get the statistics for a specific stream by ID.

        Args:
            request: The HTTP GET request.

        Returns:
            The HTTP response containing the statistics.
        """
        stream_id = request.match_info.get("stream_id")
        video_track = self._app["video_tracks"].get(stream_id)

        if video_track:
            stats = self.get_video_track_stats(video_track)
        else:
            stats = {"error": "Stream not found"}

        return web.Response(
            content_type="application/json",
            text=json.dumps(stats),
        )
