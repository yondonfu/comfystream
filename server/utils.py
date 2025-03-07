"""Utility functions for the server."""

import asyncio
import random
import types
import logging
import json
from aiohttp import web
from aiortc import MediaStreamTrack
from typing import List, Tuple, Any, Dict
import time
from collections import deque

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
        video_track = self._app["video_tracks"].get(stream_id)

        if video_track:
            stats = await self.collect_video_metrics(video_track)
        else:
            stats = {"error": "Stream not found"}

        return web.Response(
            content_type="application/json",
            text=json.dumps(stats),
        )


class FPSMeter:
    """Class to calculate and store the framerate of a stream by counting frames."""

    def __init__(self):
        """Initializes the FPSMeter class."""
        self._lock = asyncio.Lock()
        self._fps_interval_frame_count = 0
        self._last_fps_calculation_time = None
        self._fps_loop_start_time = None
        self._fps = 0.0
        self._fps_measurements = deque(maxlen=60)
        self._running_event = asyncio.Event()

        asyncio.create_task(self._calculate_fps_loop())

    async def _calculate_fps_loop(self):
        """Loop to calculate FPS periodically."""
        await self._running_event.wait()
        self._fps_loop_start_time = time.monotonic()
        while True:
            async with self._lock:
                current_time = time.monotonic()
                if self._last_fps_calculation_time is not None:
                    time_diff = current_time - self._last_fps_calculation_time
                    self._fps = self._fps_interval_frame_count / time_diff
                    self._fps_measurements.append(
                        {
                            "timestamp": current_time - self._fps_loop_start_time,
                            "fps": self._fps,
                        }
                    )  # Store the FPS measurement with timestamp

                # Reset start_time and frame_count for the next interval.
                self._last_fps_calculation_time = current_time
                self._fps_interval_frame_count = 0
            await asyncio.sleep(1)  # Calculate FPS every second.

    async def increment_frame_count(self):
        """Increment the frame count to calculate FPS."""
        async with self._lock:
            self._fps_interval_frame_count += 1
            if not self._running_event.is_set():
                self._running_event.set()

    @property
    async def fps(self) -> float:
        """Get the current output frames per second (FPS).

        Returns:
            The current output FPS.
        """
        async with self._lock:
            return self._fps

    @property
    async def fps_measurements(self) -> list:
        """Get the array of FPS measurements for the last minute.

        Returns:
            The array of FPS measurements for the last minute.
        """
        async with self._lock:
            return list(self._fps_measurements)

    @property
    async def average_fps(self) -> float:
        """Calculate the average FPS from the measurements taken in the last minute.

        Returns:
            The average FPS over the last minute.
        """
        async with self._lock:
            if not self._fps_measurements:
                return 0.0
            return sum(
                measurement["fps"] for measurement in self._fps_measurements
            ) / len(self._fps_measurements)

    @property
    async def last_fps_calculation_time(self) -> float:
        """Get the elapsed time since the last FPS calculation.

        Returns:
            The elapsed time in seconds since the last FPS calculation.
        """
        async with self._lock:
            if (
                self._last_fps_calculation_time is None
                or self._fps_loop_start_time is None
            ):
                return 0.0
            return self._last_fps_calculation_time - self._fps_loop_start_time
