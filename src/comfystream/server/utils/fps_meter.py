"""Module to calculate and store the framerate of a stream by counting frames."""

import asyncio
import logging
import time
from collections import deque
from comfystream.server.metrics import MetricsManager

logger = logging.getLogger(__name__)


class FPSMeter:
    """Class to calculate and store the framerate of a stream by counting frames."""

    def __init__(self, metrics_manager: MetricsManager, track_id: str):
        """Initializes the FPSMeter class."""
        self._lock = asyncio.Lock()
        self._fps_interval_frame_count = 0
        self._last_fps_calculation_time = None
        self._fps_loop_start_time = None
        self._fps = 0.0
        self._fps_measurements = deque(maxlen=60)
        self._running_event = asyncio.Event()
        self._metrics_manager = metrics_manager
        self.track_id = track_id

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

            # Update Prometheus metrics if enabled.
            self._metrics_manager.update_fps_metrics(self._fps, self.track_id)

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
            return (
                sum(m["fps"] for m in self._fps_measurements)
                / len(self._fps_measurements)
                if self._fps_measurements
                else self._fps
            )

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
