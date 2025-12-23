import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from pytrickle.frame_processor import FrameProcessor
from pytrickle.frames import AudioFrame, VideoFrame
from pytrickle.stream_processor import VideoProcessingResult
from utils_byoc import ComfyStreamParamsUpdateRequest, normalize_stream_params

from comfystream.pipeline import Pipeline
from comfystream.pipeline_state import PipelineState
from comfystream.utils import (
    convert_prompt,
    get_default_workflow,
)

logger = logging.getLogger(__name__)


class ComfyStreamFrameProcessor(FrameProcessor):
    """
    Integrated ComfyStream FrameProcessor for pytrickle.

    This class wraps the ComfyStream Pipeline to work with pytrickle's streaming architecture.
    """

    def __init__(self, text_poll_interval: float = 0.25, **load_params):
        """Initialize with load parameters for pipeline creation.

        Args:
            text_poll_interval: Interval in seconds to poll for text outputs (default: 0.25)
            **load_params: Parameters for pipeline creation
        """
        super().__init__()

        self.pipeline = None
        self._load_params = load_params
        self._text_poll_interval = text_poll_interval
        self._stream_processor = None
        self._warmup_task = None
        self._text_forward_task = None
        self._background_tasks = []
        self._stop_event = asyncio.Event()

    async def _apply_stream_start_prompt(self, prompt_value: Any) -> bool:
        if not self.pipeline:
            logger.debug("Cannot apply stream start prompt without pipeline")
            return False

        # Parse prompt payload from various formats
        prompt_dict = None
        if prompt_value is None:
            pass
        elif isinstance(prompt_value, dict):
            prompt_dict = prompt_value
        elif isinstance(prompt_value, list):
            for candidate in prompt_value:
                if isinstance(candidate, dict):
                    prompt_dict = candidate
                    break
        elif isinstance(prompt_value, str):
            prompt_str = prompt_value.strip()
            if prompt_str:
                try:
                    parsed = json.loads(prompt_str)
                    if isinstance(parsed, dict):
                        prompt_dict = parsed
                    else:
                        logger.warning("Parsed prompt payload is %s, expected dict", type(parsed))
                except json.JSONDecodeError:
                    logger.error("Stream start prompt is not valid JSON")
        else:
            logger.warning("Unsupported prompt payload type: %s", type(prompt_value))

        if not isinstance(prompt_dict, dict):
            logger.warning("Skipping prompt application due to invalid payload")
            return False

        try:
            await self._process_prompts(prompt_dict, skip_warmup=True)
            return True
        except Exception:
            logger.exception("Failed to apply stream start prompt")
            raise

    def _workflow_has_video(self) -> bool:
        """Return True if current workflow is expected to produce video output."""
        if not self.pipeline:
            return False
        try:
            capabilities = self.pipeline.get_workflow_io_capabilities()
            return bool(capabilities.get("video", {}).get("output", False))
        except Exception:
            logger.debug("Unable to determine workflow video capability", exc_info=True)
            return False

    def set_stream_processor(self, stream_processor):
        """Set reference to StreamProcessor for data publishing."""
        self._stream_processor = stream_processor
        logger.info("StreamProcessor reference set for text data publishing")

    def _setup_text_monitoring(self):
        """Set up background text forwarding from the pipeline."""
        try:
            if self.pipeline and self._stream_processor:
                # Reset stop event for new stream
                self._reset_stop_event()
                # Start forwarder only if workflow has text outputs (best-effort)
                should_start = True
                try:
                    should_start = bool(self.pipeline.produces_text_output())
                except Exception:
                    # If capability check fails, default to starting forwarder
                    should_start = True

                if should_start:
                    # Start a background task that forwards text outputs via StreamProcessor
                    if self._text_forward_task and not self._text_forward_task.done():
                        logger.debug("Text forwarder already running; not starting another")
                        return

                    async def _forward_text_loop():
                        try:
                            logger.info("Starting background text forwarder task")
                            while not self._stop_event.is_set():
                                try:
                                    # Non-blocking poll; sleep if no text to avoid tight loop
                                    text = await self.pipeline.get_text_output()
                                    if text is None or text.strip() == "":
                                        await asyncio.sleep(self._text_poll_interval)
                                        continue
                                    if self._stream_processor:
                                        success = await self._stream_processor.send_data(text)
                                        if not success:
                                            logger.debug(
                                                "Text send failed; stopping text forwarder"
                                            )
                                            break
                                except asyncio.CancelledError:
                                    logger.debug("Text forwarder task cancelled")
                                    raise
                        except asyncio.CancelledError:
                            # Propagate to finally for cleanup
                            raise
                        except Exception as e:
                            logger.error(f"Error in text forwarder: {e}")
                        finally:
                            logger.info("Text forwarder task exiting")

                    self._text_forward_task = asyncio.create_task(_forward_text_loop())
                    self._background_tasks.append(self._text_forward_task)
        except Exception:
            logger.warning("Failed to set up text monitoring", exc_info=True)

    def _set_loading_overlay(self, enabled: bool) -> bool:
        """Toggle the StreamProcessor loading overlay if available."""
        processor = self._stream_processor
        if not processor:
            return False
        try:
            processor.set_loading_overlay(enabled)
            logger.debug("Set loading overlay to %s", enabled)
            return True
        except Exception:
            logger.warning("Failed to update loading overlay state", exc_info=True)
            return False

    def _schedule_overlay_reset_on_ingest_enabled(self) -> None:
        """Disable the loading overlay after pipeline ingest resumes."""
        if not self.pipeline:
            self._set_loading_overlay(False)
            return

        if self.pipeline.is_ingest_enabled():
            self._set_loading_overlay(False)
            return

        async def _wait_for_ingest_enable():
            try:
                while True:
                    if self._stop_event.is_set():
                        break
                    if not self.pipeline:
                        break
                    if self.pipeline.is_ingest_enabled():
                        break
                    await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("Loading overlay watcher error", exc_info=True)
            finally:
                self._set_loading_overlay(False)

        task = asyncio.create_task(_wait_for_ingest_enable())
        self._background_tasks.append(task)

    async def _stop_text_forwarder(self) -> None:
        """Stop the background text forwarder task if running."""
        task = self._text_forward_task
        if task and not task.done():
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.debug("Error while awaiting text forwarder cancellation", exc_info=True)
        self._text_forward_task = None

    async def on_stream_stop(self):
        """Called when stream stops - cleanup background tasks."""
        logger.info("Stream stopped, cleaning up background tasks")

        # Set stop event to signal all background tasks to stop
        self._stop_event.set()

        # Stop the ComfyStream client's prompt execution
        if self.pipeline:
            logger.info("Stopping ComfyStream client prompt execution")
            try:
                await self.pipeline.stop_prompts(cleanup=True)
            except Exception as e:
                logger.error(f"Error stopping ComfyStream client: {e}")

        # Stop text forwarder
        await self._stop_text_forwarder()

        # Cancel any other background tasks started by this processor
        for task in list(self._background_tasks):
            try:
                if task and not task.done():
                    task.cancel()
            except Exception:
                continue

        # Await task cancellations
        for task in list(self._background_tasks):
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    logger.debug("Background task raised during shutdown", exc_info=True)

        self._background_tasks.clear()
        logger.info("All background tasks cleaned up")

    def _reset_stop_event(self):
        """Reset the stop event for a new stream."""
        self._stop_event.clear()

    async def on_stream_start(self, params: Optional[Dict[str, Any]] = None):
        """Handle stream start lifecycle events."""
        logger.info("Stream starting")
        self._reset_stop_event()
        logger.info(f"Stream start params: {params}")
        overlay_managed = False

        if not self.pipeline:
            logger.debug("Stream start requested before pipeline initialization")
            return

        stream_params = normalize_stream_params(params)
        stream_width = stream_params.get("width")
        stream_height = stream_params.get("height")
        stream_width = int(stream_width) if stream_width is not None else None
        stream_height = int(stream_height) if stream_height is not None else None
        prompt_payload = stream_params.pop("prompts", None)
        if prompt_payload is None:
            prompt_payload = stream_params.pop("prompt", None)

        if not prompt_payload and not self.pipeline.state_manager.is_initialized():
            logger.info(
                "No prompts provided for new stream; applying default workflow for initialization"
            )
            prompt_payload = get_default_workflow()

        if prompt_payload:
            try:
                await self._apply_stream_start_prompt(prompt_payload)
            except Exception:
                logger.exception("Failed to apply stream start prompt")
                return

        if not self.pipeline.state_manager.is_initialized():
            logger.info("Pipeline not initialized; waiting for prompts before streaming")
            return

        if stream_params:
            try:
                await self.update_params(stream_params)
            except Exception:
                logger.exception("Failed to process stream start parameters")
                return

        overlay_managed = self._set_loading_overlay(True)

        try:
            await self.pipeline.ensure_warmup(stream_width, stream_height)
        except Exception:
            if overlay_managed:
                self._set_loading_overlay(False)
            logger.exception("Failed to ensure pipeline warmup during stream start")
            return

        if overlay_managed:
            self._schedule_overlay_reset_on_ingest_enabled()

        try:
            if (
                self.pipeline.state != PipelineState.STREAMING
                and self.pipeline.state_manager.can_stream()
            ):
                await self.pipeline.start_streaming()

            if self.pipeline.produces_text_output():
                self._setup_text_monitoring()
            else:
                await self._stop_text_forwarder()
        except Exception:
            logger.exception("Failed during stream start", exc_info=True)

    async def load_model(self, **kwargs):
        """Load model and initialize the pipeline."""
        params = {**self._load_params, **kwargs}

        if self.pipeline is None:
            self.pipeline = Pipeline(
                width=int(params.get("width", 512)),
                height=int(params.get("height", 512)),
                cwd=params.get("workspace", os.getcwd()),
                disable_cuda_malloc=params.get("disable_cuda_malloc", True),
                gpu_only=params.get("gpu_only", True),
                preview_method=params.get("preview_method", "none"),
                comfyui_inference_log_level=params.get("comfyui_inference_log_level", "INFO"),
                logging_level=params.get("comfyui_inference_log_level", "INFO"),
                blacklist_custom_nodes=["ComfyUI-Manager"],
            )
            await self.pipeline.initialize()

    async def warmup(self):
        """Warm up the pipeline."""
        if not self.pipeline:
            logger.warning("Warmup requested before pipeline initialization")
            return

        logger.info("Running pipeline warmup...")
        try:
            capabilities = self.pipeline.get_workflow_io_capabilities()
            logger.info(f"Detected I/O capabilities: {capabilities}")

            await self.pipeline.warmup()

        except Exception as e:
            logger.error(f"Warmup failed: {e}")

    def _schedule_warmup(self) -> None:
        """Schedule warmup in background if not already running."""
        try:
            if self._warmup_task and not self._warmup_task.done():
                logger.info("Warmup already in progress, skipping new warmup request")
                return

            self._warmup_task = asyncio.create_task(self.warmup())
            logger.info("Warmup scheduled in background")
        except Exception:
            logger.warning("Failed to schedule warmup", exc_info=True)

    async def process_video_async(
        self, frame: VideoFrame
    ) -> Union[VideoFrame, VideoProcessingResult]:
        """Process video frame through ComfyStream Pipeline.

        Returns VideoProcessingResult.WITHHELD to trigger pytrickle's automatic overlay when
        processed frames are not yet available.
        """
        try:
            if not self.pipeline:
                return frame

            # TODO: Do we really need this here?
            await self.pipeline.ensure_warmup()

            if not self.pipeline.state_manager.is_initialized():
                return VideoProcessingResult.WITHHELD

            # If pipeline ingestion is paused, withhold frame so pytrickle renders the overlay
            if not self.pipeline.is_ingest_enabled():
                return VideoProcessingResult.WITHHELD

            # Convert pytrickle VideoFrame to av.VideoFrame
            av_frame = frame.to_av_frame(frame.tensor)
            av_frame.pts = frame.timestamp
            av_frame.time_base = frame.time_base

            # Process through pipeline
            await self.pipeline.put_video_frame(av_frame)

            processed_av_frame = await self.pipeline.get_processed_video_frame()
            processed_frame = VideoFrame.from_av_frame_with_timing(processed_av_frame, frame)
            return processed_frame

        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return frame

    async def process_audio_async(self, frame: AudioFrame) -> List[AudioFrame]:
        """Process audio frame through ComfyStream Pipeline or passthrough."""
        try:
            if not self.pipeline:
                return [frame]

            # If pipeline ingestion is paused, passthrough audio
            if not self.pipeline.is_ingest_enabled():
                frame.side_data.skipped = True
                frame.side_data.passthrough = True
                return [frame]

            # Audio processing - use pipeline
            av_frame = frame.to_av_frame()
            await self.pipeline.put_audio_frame(av_frame)
            processed_av_frame = await self.pipeline.get_processed_audio_frame()
            processed_frame = AudioFrame.from_av_audio(processed_av_frame)
            return [processed_frame]

        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return [frame]

    async def update_params(self, params: dict):
        """Update processing parameters."""
        if not self.pipeline:
            return

        params_payload: Dict[str, Any] = {}
        if isinstance(params, list):
            params = params[0] if params else {}

        if isinstance(params, dict):
            params_payload = dict(params)
        elif params is None:
            params_payload = {}
        else:
            logger.warning("Unsupported params type for update_params: %s", type(params))
            return

        if not params_payload:
            return

        # Validate parameters using the centralized validation
        validated = ComfyStreamParamsUpdateRequest(**params_payload).model_dump()
        logger.info(f"Parameter validation successful, keys: {list(validated.keys())}")

        # Process prompts if provided
        if "prompts" in validated and validated["prompts"]:
            await self._process_prompts(validated["prompts"], skip_warmup=True)

        # Update pipeline dimensions
        if "width" in validated:
            self.pipeline.width = int(validated["width"])
        if "height" in validated:
            self.pipeline.height = int(validated["height"])

    async def _process_prompts(self, prompts, *, skip_warmup: bool = False):
        """Process and set prompts in the pipeline."""
        if not self.pipeline:
            logger.warning("Prompt update requested before pipeline initialization")
            return
        try:
            converted = convert_prompt(prompts, return_dict=True)

            await self.pipeline.apply_prompts(
                [converted],
                skip_warmup=skip_warmup,
            )

            if self.pipeline.state_manager.can_stream():
                await self.pipeline.start_streaming()

            logger.info(f"Prompts applied successfully: {list(prompts.keys())}")

            if self.pipeline.produces_text_output():
                self._setup_text_monitoring()
            else:
                await self._stop_text_forwarder()

        except Exception as e:
            logger.error(f"Failed to process prompts: {e}")
            raise
