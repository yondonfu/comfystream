"""Module to calculate and store the framerate of a stream by counting frames."""

import asyncio
import logging
import time
from collections import deque
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class FPSMeter:
    """Class to calculate and store the framerate of a stream by counting frames.

    Attributes:
        track_id: The ID of the track.
    """

    def __init__(
        self,
        track_id: str,
        track_kind: str,
        update_metrics_callback: Optional[Callable[[float, str], None]] = None,
    ):
        """Initializes the FPSMeter class.

        Args:
            track_id: The ID of the track.
            track_kind: The kind of the track (e.g., "video" or "audio").
            update_metrics_callback: An optional callback function to update Prometheus
                metrics with FPS data.
        """
        self.track_id = track_id
        self.track_kind = track_kind
        self._lock = asyncio.Lock()
        self._fps_interval_frame_count = 0
        self._last_fps_calculation_time = None
        self._fps_loop_start_time = None
        self._fps = 0.0
        self._fps_measurements = deque(maxlen=60)
        self._running_event = asyncio.Event()
        self._update_metrics_callback = update_metrics_callback

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
                    self._fps = (
                        self._fps_interval_frame_count / time_diff
                        if time_diff > 0
                        else 0.0
                    )
                    self._fps_measurements.append(
                        {
                            "timestamp": current_time - self._fps_loop_start_time,
                            "fps": self._fps,
                        }
                    )  # Store the FPS measurement with timestamp

                # Reset tracking variables for the next interval.
                self._last_fps_calculation_time = current_time
                self._fps_interval_frame_count = 0

            # Update Prometheus metrics using the callback if provided.
            if self._update_metrics_callback:
                self._update_metrics_callback(self._fps, self.track_id, self.track_kind)

            await asyncio.sleep(1)  # Calculate FPS every second.

    async def increment_frame_count(self):
        """Increment the frame count to calculate FPS."""
        async with self._lock:
            self._fps_interval_frame_count += 1
            if not self._running_event.is_set():
                self._running_event.set()

    async def get_fps(self) -> float:
        """Get the current output frames per second (FPS).

        Returns:
            The current output FPS.
        """
        async with self._lock:
            return self._fps

    async def get_fps_measurements(self) -> list:
        """Get the array of FPS measurements for the last minute.

        Returns:
            The array of FPS measurements for the last minute.
        """
        async with self._lock:
            return list(self._fps_measurements)

    async def get_average_fps(self) -> float:
        """Calculate the average FPS from the measurements taken in the last minute.

        Returns:
            The average FPS over the last minute.
        """
        async with self._lock:
            return (
                sum(m["fps"] for m in self._fps_measurements)
                / len(self._fps_measurements)
                if self._fps_measurements
                else self._fps
            )

    async def get_last_fps_calculation_time(self) -> float:
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
