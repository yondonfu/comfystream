import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union

import av
import numpy as np
import torch

from comfystream.client import ComfyStreamClient
from comfystream.pipeline_state import PipelineState, PipelineStateManager
from comfystream.server.utils import temporary_log_level
from comfystream.utils import get_default_workflow

from .modalities import (
    WorkflowModality,
    create_empty_workflow_modality,
    detect_io_points,
    detect_prompt_modalities,
)

WARMUP_RUNS = 5
BOOTSTRAP_TIMEOUT_SECONDS = 30.0

logger = logging.getLogger(__name__)


class Pipeline:
    """A pipeline for processing video and audio frames using ComfyUI.

    This class provides a high-level interface for processing video and audio frames
    through a ComfyUI-based processing pipeline. It handles frame preprocessing,
    postprocessing, and queue management.
    """

    def __init__(
        self,
        width: int = 512,
        height: int = 512,
        comfyui_inference_log_level: Optional[int] = None,
        auto_warmup: bool = False,
        bootstrap_default_prompt: bool = True,
        **kwargs,
    ):
        """Initialize the pipeline with the given configuration.

        Args:
            width: Width of the video frames (default: 512)
            height: Height of the video frames (default: 512)
            comfyui_inference_log_level: The logging level for ComfyUI inference.
                Defaults to None, using the global ComfyUI log level.
            auto_warmup: Whether to run warmup automatically after prompts are set.
            bootstrap_default_prompt: Whether to run the default workflow once during
                initialization to start ComfyUI before prompts are applied.
            **kwargs: Additional arguments to pass to the ComfyStreamClient
        """
        self.client = ComfyStreamClient(**kwargs)
        self.width = width
        self.height = height
        self.auto_warmup = auto_warmup
        self.bootstrap_default_prompt = bootstrap_default_prompt

        self.video_incoming_frames = asyncio.Queue()
        self.audio_incoming_frames = asyncio.Queue()

        self.processed_audio_buffer = np.array([], dtype=np.int16)

        self._comfyui_inference_log_level = comfyui_inference_log_level
        self._cached_modalities: Optional[Set[str]] = None
        self._cached_io_capabilities: Optional[WorkflowModality] = None
        self.state_manager = PipelineStateManager(self.client)
        self._bootstrap_completed = False
        self._initialize_lock = asyncio.Lock()
        self._ingest_enabled = True
        self._prompt_update_lock = asyncio.Lock()

    @property
    def state(self) -> PipelineState:
        """Expose current pipeline state."""
        return self.state_manager.state

    async def initialize(self):
        """Run optional bootstrap workflow to start ComfyUI before prompts are set."""
        if self._bootstrap_completed or not self.bootstrap_default_prompt:
            return

        async with self._initialize_lock:
            if self._bootstrap_completed or not self.bootstrap_default_prompt:
                return

            logger.info("Bootstrapping ComfyUI with default workflow")
            await self._run_bootstrap_prompt()
            self._bootstrap_completed = True

    async def _run_bootstrap_prompt(self):
        """Run the default workflow once with a dummy frame to start ComfyUI."""
        default_workflow = get_default_workflow()
        logger.debug("Running default workflow bootstrap prompt")

        try:
            await self.client.set_prompts([default_workflow])
            await self.client.resume_prompts()

            dummy_frame = av.VideoFrame()
            dummy_frame.side_data.input = torch.randn(1, self.height, self.width, 3)
            self.client.put_video_input(dummy_frame)

            await asyncio.wait_for(
                self.client.get_video_output(),
                timeout=BOOTSTRAP_TIMEOUT_SECONDS,
            )
            logger.info("Bootstrap prompt completed successfully")
        except asyncio.TimeoutError as exc:
            logger.error("Timeout while waiting for bootstrap prompt output")
            raise RuntimeError("Bootstrap prompt timed out while waiting for output") from exc
        finally:
            try:
                await self.client.stop_prompts(cleanup=False)
            except Exception:
                logger.debug("Failed to stop bootstrap prompts cleanly", exc_info=True)

            self.client.current_prompts = []
            self._cached_modalities = None
            self._cached_io_capabilities = None

            try:
                await self.client.cleanup_queues()
            except Exception:
                logger.debug("Failed to clear tensor caches after bootstrap prompt", exc_info=True)

    async def warmup(
        self,
        *,
        warm_video: Optional[bool] = None,
        warm_audio: Optional[bool] = None,
    ):
        """Run warmup for selected modalities while managing pipeline state."""
        if not self.state_manager.is_initialized():
            raise RuntimeError("Cannot warm up pipeline before prompts are initialized")

        state_before = self.state
        transitioned = False
        warmup_successful = False

        try:
            if state_before != PipelineState.STREAMING:
                await self.state_manager.transition_to(PipelineState.INITIALIZING)
                transitioned = True

            await self._run_warmup(
                warm_video=warm_video,
                warm_audio=warm_audio,
            )
            warmup_successful = True
        except Exception:
            await self.state_manager.transition_to(PipelineState.ERROR)
            raise
        finally:
            if transitioned and warmup_successful:
                try:
                    await self.state_manager.transition_to(PipelineState.READY)
                except Exception:
                    logger.exception("Failed to transition pipeline to READY after warmup")
                    warmup_successful = False

            if warmup_successful and state_before == PipelineState.STREAMING:
                try:
                    await self.state_manager.transition_to(PipelineState.STREAMING)
                except Exception:
                    logger.exception("Failed to restore STREAMING state after warmup")

    async def _run_warmup(
        self,
        *,
        warm_video: Optional[bool] = None,
        warm_audio: Optional[bool] = None,
    ):
        """Run warmup routines for video and audio as requested."""
        capabilities = self.get_workflow_io_capabilities()

        video_config = capabilities.get("video", {})
        audio_config = capabilities.get("audio", {})

        should_warm_video = (
            warm_video
            if warm_video is not None
            else bool(video_config.get("input") or video_config.get("output"))
        )
        should_warm_audio = (
            warm_audio
            if warm_audio is not None
            else bool(audio_config.get("input") or audio_config.get("output"))
        )

        if should_warm_video:
            logger.debug("Running video warmup routine")
            await self.warm_video()

        if should_warm_audio:
            logger.debug("Running audio warmup routine")
            await self.warm_audio()

        logger.info(
            "Pipeline warmup completed (video=%s, audio=%s)",
            should_warm_video,
            should_warm_audio,
        )

    async def warm_video(self):
        """Warm up the video processing pipeline with dummy frames."""
        # Only warm if workflow accepts video input
        if not self.accepts_video_input():
            logger.debug("Skipping video warmup - workflow doesn't accept video input")
            return

        # Create dummy frame with the CURRENT resolution settings
        dummy_frame = av.VideoFrame()
        dummy_frame.side_data.input = torch.randn(1, self.height, self.width, 3)

        logger.debug(f"Warming video pipeline with resolution {self.width}x{self.height}")

        for _ in range(WARMUP_RUNS):
            self.client.put_video_input(dummy_frame)

            # Wait on the outputs that the workflow actually produces
            if self.produces_video_output():
                await self.client.get_video_output()
            if self.produces_audio_output():
                await self.client.get_audio_output()
            if self.produces_text_output():
                await self.client.get_text_output()

    async def warm_audio(self):
        """Warm up the audio processing pipeline with dummy frames."""
        # Only warm if workflow accepts audio input
        if not self.accepts_audio_input():
            logger.debug("Skipping audio warmup - workflow doesn't accept audio input")
            return

        dummy_frame = av.AudioFrame()
        dummy_frame.side_data.input = np.random.randint(
            -32768, 32768, int(48000 * 0.5), dtype=np.int16
        )
        dummy_frame.sample_rate = 48000

        for _ in range(WARMUP_RUNS):
            self.client.put_audio_input(dummy_frame)

            # Wait on the outputs that the workflow actually produces
            if self.produces_video_output():
                await self.client.get_video_output()
            if self.produces_audio_output():
                await self.client.get_audio_output()
            if self.produces_text_output():
                await self.client.get_text_output()

    async def set_prompts(
        self,
        prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]],
        *,
        skip_warmup: bool = False,
    ):
        """Set the processing prompts for the pipeline.

        Args:
            prompts: Either a single prompt dictionary or a list of prompt dictionaries
            skip_warmup: Skip automatic warmup even if auto_warmup is enabled
        """
        try:
            prompt_list = prompts if isinstance(prompts, list) else [prompts]
            await self.client.set_prompts(prompt_list)

            # Refresh cached modalities and I/O capabilities from the new prompts
            self._cached_modalities = detect_prompt_modalities(self.client.current_prompts)
            self._cached_io_capabilities = detect_io_points(self.client.current_prompts)

            should_warmup = self.auto_warmup and not skip_warmup
            if should_warmup:
                await self.state_manager.transition_to(PipelineState.INITIALIZING)
                try:
                    await self._run_warmup()
                except Exception:
                    await self.state_manager.transition_to(PipelineState.ERROR)
                    raise

            await self.state_manager.transition_to(PipelineState.READY)
        except Exception:
            logger.exception("Failed to set pipeline prompts")
            try:
                await self.state_manager.transition_to(PipelineState.ERROR)
            except ValueError:
                logger.debug("Skipping ERROR transition due to invalid state")
            except Exception:
                logger.exception("Failed to transition pipeline to ERROR state")
            raise

    async def update_prompts(
        self,
        prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]],
        *,
        skip_warmup: bool = False,
    ):
        """Update the existing processing prompts.

        Args:
            prompts: Either a single prompt dictionary or a list of prompt dictionaries
            skip_warmup: Skip automatic warmup even if auto_warmup is enabled
        """
        was_streaming = self.state == PipelineState.STREAMING
        should_warmup = self.auto_warmup and not skip_warmup

        try:
            if was_streaming and should_warmup:
                await self.state_manager.transition_to(PipelineState.READY)

            prompt_list = prompts if isinstance(prompts, list) else [prompts]
            await self.client.update_prompts(prompt_list)

            # Refresh cached modalities and I/O capabilities from the updated prompts
            self._cached_modalities = detect_prompt_modalities(self.client.current_prompts)
            self._cached_io_capabilities = detect_io_points(self.client.current_prompts)

            if should_warmup:
                await self.state_manager.transition_to(PipelineState.INITIALIZING)
                try:
                    await self._run_warmup()
                except Exception:
                    await self.state_manager.transition_to(PipelineState.ERROR)
                    raise
                await self.state_manager.transition_to(PipelineState.READY)

            if was_streaming and self.state != PipelineState.STREAMING:
                await self.state_manager.transition_to(PipelineState.STREAMING)
        except Exception:
            logger.exception("Failed to update pipeline prompts")
            try:
                await self.state_manager.transition_to(PipelineState.ERROR)
            except ValueError:
                logger.debug("Skipping ERROR transition due to invalid state")
            except Exception:
                logger.exception("Failed to transition pipeline to ERROR state")
            raise

    def disable_ingest(self) -> None:
        """Temporarily disable ingestion of new frames into the pipeline."""
        self._ingest_enabled = False

    def enable_ingest(self) -> None:
        """Re-enable ingestion of new frames into the pipeline."""
        self._ingest_enabled = True

    def is_ingest_enabled(self) -> bool:
        """Check if the pipeline is currently ingesting new frames."""
        return self._ingest_enabled

    async def apply_prompts(
        self,
        prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]],
        *,
        skip_warmup: bool = False,
        warm_video: Optional[bool] = None,
        warm_audio: Optional[bool] = None,
    ) -> WorkflowModality:
        """Atomically replace prompts while coordinating runner, queues, and state.

        This helper orchestrates prompt swaps by pausing streaming, cancelling any
        in-flight prompt execution, clearing input queues, applying the new prompts,
        warming the pipeline (unless explicitly skipped), and finally resuming
        streaming if it was active beforehand.

        Args:
            prompts: Prompt dictionary or list of prompt dictionaries to apply.
            skip_warmup: If True, skip automatic warmup after applying prompts.
            warm_video: Optional override for video warmup (None = auto-detect).
            warm_audio: Optional override for audio warmup (None = auto-detect).

        Returns:
            WorkflowModality describing I/O capabilities detected from the new prompts.
        """
        prompt_list = prompts if isinstance(prompts, list) else [prompts]

        async with self._prompt_update_lock:
            was_streaming = self.state == PipelineState.STREAMING
            was_initialized = self.state_manager.is_initialized()
            restart_streaming = False
            capabilities: WorkflowModality | None = None
            self.disable_ingest()

            try:
                if was_streaming:
                    await self.pause_prompts()

                if was_initialized:
                    await self.stop_prompts_immediately()

                await self._clear_pipeline_queues()
                await self.client.cleanup_queues()

                await self.set_prompts(prompt_list, skip_warmup=True)

                capabilities = self.get_workflow_io_capabilities()
                video_capability = capabilities.get("video", {})
                audio_capability = capabilities.get("audio", {})

                has_video_io = bool(video_capability.get("input") or video_capability.get("output"))
                has_audio_io = bool(audio_capability.get("input") or audio_capability.get("output"))

                if not skip_warmup:
                    await self.warmup(
                        warm_video=warm_video if warm_video is not None else has_video_io,
                        warm_audio=warm_audio if warm_audio is not None else has_audio_io,
                    )

                restart_streaming = was_streaming and self.state_manager.can_stream()

            except Exception:
                raise
            finally:
                self.enable_ingest()
                if restart_streaming and self.state_manager.can_stream():
                    await self.start_streaming()

            return capabilities if capabilities is not None else self.get_workflow_io_capabilities()

    async def start_streaming(self):
        """Enable prompt execution for active streaming."""
        if not self.state_manager.can_stream():
            raise RuntimeError(f"Cannot start streaming in state: {self.state.name}")

        await self.state_manager.transition_to(PipelineState.STREAMING)

    async def stop_streaming(self):
        """Pause prompt execution while keeping prompts loaded."""
        if self.state == PipelineState.STREAMING:
            await self.state_manager.transition_to(PipelineState.READY)

    async def pause_prompts(self):
        """Pause prompt execution loops without canceling tasks."""
        await self.stop_streaming()

    async def resume_prompts(self):
        """Resume paused prompt execution loops."""
        await self.start_streaming()

    def are_prompts_running(self) -> bool:
        """Check if prompts are currently running.

        Returns:
            True if prompts are enabled and running, False otherwise
        """
        return self.state == PipelineState.STREAMING

    async def stop_prompts(self, cleanup: bool = False):
        """Stop running prompts by canceling their tasks.

        Args:
            cleanup: If True, perform full cleanup including queue clearing and
                client shutdown. If False, only cancel prompt tasks.
        """
        if self.state in {PipelineState.STREAMING, PipelineState.INITIALIZING}:
            await self.state_manager.transition_to(PipelineState.READY)

        await self.client.stop_prompts(cleanup=cleanup)

        # Clear cached modalities and I/O capabilities when prompts are stopped
        if cleanup:
            self._cached_modalities = None
            self._cached_io_capabilities = None
            # Clear pipeline queues for full cleanup
            await self._clear_pipeline_queues()
            try:
                await self.state_manager.transition_to(PipelineState.UNINITIALIZED)
            except Exception:
                logger.exception("Failed to transition pipeline to UNINITIALIZED during cleanup")
        else:
            try:
                await self.state_manager.transition_to(PipelineState.READY)
            except ValueError:
                logger.debug("Skipping READY transition due to invalid state")
            except Exception:
                logger.exception("Failed to ensure READY state after stopping prompts")

    async def stop_prompts_immediately(self):
        """Cancel prompt execution tasks without full cleanup."""
        await self.client.stop_prompts_immediately()
        try:
            await self.state_manager.transition_to(PipelineState.READY)
        except ValueError:
            logger.debug("Skipping READY transition during immediate stop")
        except Exception:
            logger.exception("Failed to ensure READY state during immediate stop")

    async def put_video_frame(self, frame: av.VideoFrame):
        """Queue a video frame for processing.

        Args:
            frame: The video frame to process
        """
        # Check if workflow accepts video input
        if not self.accepts_video_input():
            # Mark frame as skipped and don't send to client
            frame.side_data.skipped = True
            frame.side_data.passthrough = True
            await self.video_incoming_frames.put(frame)
            return

        # Process and send to client only if input is accepted
        frame.side_data.input = self.video_preprocess(frame)
        frame.side_data.skipped = True
        frame.side_data.passthrough = False
        self.client.put_video_input(frame)
        await self.video_incoming_frames.put(frame)

    async def put_audio_frame(self, frame: av.AudioFrame, preprocess: bool = True):
        """Queue an audio frame for processing.

        Args:
            frame: The audio frame to process
        """
        # Check if workflow accepts audio input
        if not self.accepts_audio_input():
            # Mark frame as skipped and don't send to client
            frame.side_data.skipped = True
            frame.side_data.passthrough = True
            await self.audio_incoming_frames.put(frame)
            return

        # Process and send to client when input is accepted
        frame.side_data.input = self.audio_preprocess(frame) if preprocess else frame.to_ndarray()
        frame.side_data.skipped = True
        # Mark passthrough based on whether workflow produces audio output
        frame.side_data.passthrough = not self.produces_audio_output()
        self.client.put_audio_input(frame)
        await self.audio_incoming_frames.put(frame)

    def video_preprocess(self, frame: av.VideoFrame) -> torch.Tensor:
        """Preprocess a video frame before processing.

        Args:
            frame: The video frame to preprocess

        Returns:
            The preprocessed frame as a tensor or numpy array
        """
        frame_np = frame.to_ndarray(format="rgb24").astype(np.float32) / 255.0
        return torch.from_numpy(frame_np).unsqueeze(0)

    def audio_preprocess(self, frame: av.AudioFrame) -> np.ndarray:
        """Preprocess an audio frame before processing.

        Args:
            frame: The audio frame to preprocess

        Returns:
            The preprocessed frame as a numpy array with int16 dtype
        """
        audio_data = frame.to_ndarray()

        # Handle multi-dimensional audio data
        if (
            audio_data.ndim == 2
            and audio_data.shape[0] == 1
            and audio_data.shape[0] <= audio_data.shape[1]
        ):
            audio_data = audio_data.ravel().reshape(-1, 2).mean(axis=1)
        elif audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=0)

        # Ensure we always return int16 data
        if audio_data.dtype in [np.float32, np.float64]:
            # Check if data is normalized (-1.0 to 1.0 range)
            max_abs_val = np.abs(audio_data).max()
            if max_abs_val <= 1.0:
                # Normalized float input - scale to int16 range
                audio_data = np.clip(audio_data, -1.0, 1.0)
                audio_data = (audio_data * 32767).astype(np.int16)
            else:
                # Large float values - clip and convert directly
                audio_data = np.clip(audio_data, -32768, 32767).astype(np.int16)
        else:
            # Already integer data - ensure it's int16
            audio_data = audio_data.astype(np.int16)

        return audio_data

    def video_postprocess(self, output: Union[torch.Tensor, np.ndarray]) -> av.VideoFrame:
        """Postprocess a video frame after processing.

        Args:
            output: The processed output tensor or numpy array

        Returns:
            The postprocessed video frame
        """
        return av.VideoFrame.from_ndarray(
            (output * 255.0).clamp(0, 255).to(dtype=torch.uint8).squeeze(0).cpu().numpy()
        )

    def audio_postprocess(self, output: Union[torch.Tensor, np.ndarray]) -> av.AudioFrame:
        """Postprocess an audio frame after processing.

        Args:
            output: The processed output tensor or numpy array

        Returns:
            The postprocessed audio frame
        """
        return av.AudioFrame.from_ndarray(np.repeat(output, 2).reshape(1, -1))

    # TODO: make it generic to support purely generative video cases
    async def get_processed_video_frame(self) -> av.VideoFrame:
        """Get the next processed video frame.

        Returns:
            The processed video frame, or original frame if no processing needed
        """
        frame = await self.video_incoming_frames.get()

        # Skip frames that were marked as skipped
        while frame.side_data.skipped and not hasattr(frame.side_data, "passthrough"):
            frame = await self.video_incoming_frames.get()

        # If this is a passthrough frame (no video output from workflow), return original
        if hasattr(frame.side_data, "passthrough") and frame.side_data.passthrough:
            return frame

        # Get processed output from client
        async with temporary_log_level("comfy", self._comfyui_inference_log_level):
            out_tensor = await self.client.get_video_output()

        processed_frame = self.video_postprocess(out_tensor)
        processed_frame.pts = frame.pts
        processed_frame.time_base = frame.time_base

        return processed_frame

    async def get_processed_audio_frame(self) -> av.AudioFrame:
        """Get the next processed audio frame.

        Returns:
            The processed audio frame, or original frame if no processing needed
        """
        try:
            # Add timeout to detect if no frames are being put in the queue
            frame = await asyncio.wait_for(self.audio_incoming_frames.get(), timeout=1.0)
        except asyncio.TimeoutError:
            logger.debug("No audio frames available - generating silence frame")
            # Generate a silent audio frame to prevent blocking
            silent_frame = av.AudioFrame.from_ndarray(
                np.zeros((1, 1024), dtype=np.int16), format="s16", layout="mono"
            )
            silent_frame.sample_rate = 48000
            return silent_frame

        # If this is a passthrough frame (no audio output from workflow), return original
        if hasattr(frame.side_data, "passthrough") and frame.side_data.passthrough:
            return frame

        # Process audio if needed
        if frame.samples > len(self.processed_audio_buffer):
            async with temporary_log_level("comfy", self._comfyui_inference_log_level):
                out_tensor = await self.client.get_audio_output()
            self.processed_audio_buffer = np.concatenate([self.processed_audio_buffer, out_tensor])

        out_data = self.processed_audio_buffer[: frame.samples]
        self.processed_audio_buffer = self.processed_audio_buffer[frame.samples :]

        processed_frame = self.audio_postprocess(out_data)
        processed_frame.pts = frame.pts
        processed_frame.time_base = frame.time_base
        processed_frame.sample_rate = frame.sample_rate

        return processed_frame

    async def get_text_output(self) -> str | None:
        """Get the next text output from the pipeline.

        Returns:
            The processed text output, or empty string if no text output produced
        """
        # If workflow doesn't produce text output, return empty string immediately
        if not self.produces_text_output():
            return None

        async with temporary_log_level("comfy", self._comfyui_inference_log_level):
            out_text = await self.client.get_text_output()

        return out_text

    async def get_nodes_info(self) -> Dict[str, Any]:
        """Get information about all nodes in the current prompt including metadata.

        Returns:
            Dictionary containing node information
        """
        nodes_info = await self.client.get_available_nodes()
        return nodes_info

    def get_workflow_io_capabilities(self) -> WorkflowModality:
        """Get the I/O capabilities for each modality in the current workflow.

        Returns:
            WorkflowModality mapping each modality to its input/output capabilities
        """
        if self._cached_io_capabilities is None:
            if not hasattr(self.client, "current_prompts") or not self.client.current_prompts:
                # Cache empty capabilities if no prompts to avoid repeated checks
                self._cached_io_capabilities = create_empty_workflow_modality()
            else:
                self._cached_io_capabilities = detect_io_points(self.client.current_prompts)

        return self._cached_io_capabilities

    def get_workflow_modalities(self) -> Set[str]:
        """Get the modalities required by the current workflow.

        Returns:
            Set of modality strings: {'video', 'audio', 'text'}
        """
        if self._cached_modalities is None:
            if not hasattr(self.client, "current_prompts") or not self.client.current_prompts:
                # Cache empty set if no prompts to avoid repeated checks
                self._cached_modalities = set()
            else:
                self._cached_modalities = detect_prompt_modalities(self.client.current_prompts)

        return self._cached_modalities

    def get_modalities(self) -> Set[str]:
        """Alias for get_workflow_modalities for compatibility."""
        return self.get_workflow_modalities()

    def requires_video(self) -> bool:
        """Check if the workflow requires video processing."""
        return "video" in self.get_workflow_modalities()

    def requires_audio(self) -> bool:
        """Check if the workflow requires audio processing."""
        return "audio" in self.get_workflow_modalities()

    def requires_text(self) -> bool:
        """Check if the workflow requires text processing."""
        return "text" in self.get_workflow_modalities()

    def accepts_video_input(self) -> bool:
        """Check if the workflow accepts video input."""
        return self.get_workflow_io_capabilities()["video"]["input"]

    def accepts_audio_input(self) -> bool:
        """Check if the workflow accepts audio input."""
        return self.get_workflow_io_capabilities()["audio"]["input"]

    def produces_video_output(self) -> bool:
        """Check if the workflow produces video output."""
        return self.get_workflow_io_capabilities()["video"]["output"]

    def produces_audio_output(self) -> bool:
        """Check if the workflow produces audio output."""
        return self.get_workflow_io_capabilities()["audio"]["output"]

    def produces_text_output(self) -> bool:
        """Check if the workflow produces text output."""
        return self.get_workflow_io_capabilities()["text"]["output"]

    async def cleanup(self):
        """Clean up resources used by the pipeline.

        This includes:
        - Canceling running prompts
        - Clearing all queues (video, audio, tensor caches)
        - Stopping the ComfyUI client
        - Clearing cached modalities
        """
        logger.debug("Starting pipeline cleanup")

        # Clear cached modalities and I/O capabilities since we're resetting
        self._cached_modalities = None
        self._cached_io_capabilities = None

        # Clear pipeline queues
        await self._clear_pipeline_queues()

        # Cleanup client (this handles prompt cancellation and tensor cache cleanup)
        await self.client.cleanup()

        try:
            await self.state_manager.transition_to(PipelineState.UNINITIALIZED)
        except ValueError:
            logger.debug("Skipping UNINITIALIZED transition during cleanup")
        except Exception:
            logger.exception("Failed to transition pipeline to UNINITIALIZED during cleanup")

        logger.debug("Pipeline cleanup completed")

    async def _clear_pipeline_queues(self):
        """Clear the pipeline's internal frame queues."""
        # Clear video frame queue
        while not self.video_incoming_frames.empty():
            try:
                self.video_incoming_frames.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Clear audio frame queue
        while not self.audio_incoming_frames.empty():
            try:
                self.audio_incoming_frames.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Reset audio buffer
        self.processed_audio_buffer = np.array([], dtype=np.int16)

        logger.debug("Pipeline queues cleared")
