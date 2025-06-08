import av
import torch
import numpy as np
import asyncio
import logging
from typing import Any, Dict, Union, List, Optional

from comfystream.client import ComfyStreamClient
from comfystream.server.utils import temporary_log_level

WARMUP_RUNS = 5

logger = logging.getLogger(__name__)


class Pipeline:
    """A pipeline for processing video and audio frames using ComfyUI.
    
    This class provides a high-level interface for processing video and audio frames
    through a ComfyUI-based processing pipeline. It handles frame preprocessing,
    postprocessing, and queue management.
    """
    
    def __init__(self, width: int = 512, height: int = 512, 
                 comfyui_inference_log_level: Optional[int] = None, **kwargs):
        """Initialize the pipeline with the given configuration.
        
        Args:
            width: Width of the video frames (default: 512)
            height: Height of the video frames (default: 512)
            comfyui_inference_log_level: The logging level for ComfyUI inference.
                Defaults to None, using the global ComfyUI log level.
        """
        # Store basic parameters
        self.width = width
        self.height = height
        self._comfyui_inference_log_level = comfyui_inference_log_level
        self.client = None
        self._start_lock = asyncio.Lock()
        self.video_incoming_frames = asyncio.Queue()
        self.audio_incoming_frames = asyncio.Queue()
        self.processed_audio_buffer = np.array([], dtype=np.int16)
        self._error_handler_task = None
        self._is_running = False
        self._frame_processing_task = None
        self.video_track = None
        self._startup_event = asyncio.Event()

    async def start(self, prompts: Optional[Union[Dict[Any, Any], List[Dict[Any, Any]]]] = None, **client_kwargs):
        """Start the pipeline and error monitoring."""
        async with self._start_lock:
            
            # Initialize client first
            if self.client is None or self.client.cleanup_lock.locked():
                logger.info("Initializing new client for pipeline")
                self.client = ComfyStreamClient(**client_kwargs)
                await self.client.start_error_monitor()
            
            # Set running state after client is initialized
            self._is_running = True
            
            # Start error handler
            self._error_handler_task = asyncio.create_task(self._handle_errors())
            
            # Run prompts if provided
            if prompts:
                await self.client.set_prompts(prompts)
            
            # Signal that pipeline is ready
            self._startup_event.set()
            
            # Start video track if it exists
            if self.video_track:
                await self.video_track.start()

    async def stop(self):
        """Stop the pipeline and error monitoring."""
        if not self._is_running:
            return
        
        self._is_running = False
        self._startup_event.clear()
        
        # Cancel error handler
        if self._error_handler_task:
            self._error_handler_task.cancel()
            try:
                await self._error_handler_task
            except asyncio.CancelledError:
                pass
            self._error_handler_task = None

        # Clear video queue
        while not self.video_incoming_frames.empty():
            try:
                frame = self.video_incoming_frames.get_nowait()
                self._unload_frame_tensors(frame)
            except Exception as e:
                logger.error(f"Error clearing video queue: {e}")

        # Clear audio queue  
        while not self.audio_incoming_frames.empty():
            try:
                frame = self.audio_incoming_frames.get_nowait()
                self._unload_frame_tensors(frame)
            except Exception as e:
                logger.error(f"Error clearing audio queue: {e}")
                
        self.processed_audio_buffer = np.array([], dtype=np.int16)
        await self.client.stop_error_monitor()
        await self.client.cleanup(exit_client=True)

    async def _handle_errors(self):
        """Handle errors from the client."""
        while self._is_running:
            try:
                error = await self.client.error_queue.get()
                logger.error(f"Pipeline error: {error}")
                self.client.error_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in error handler: {e}")

    async def set_prompts(self, prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]]):
        """Set the processing prompts for the pipeline.
        
        Args:
            prompts: Either a single prompt dictionary or a list of prompt dictionaries
        """
        if self.client is None:
            raise RuntimeError("Pipeline client not initialized. Call start() first.")
            
        if isinstance(prompts, list):
            await self.client.set_prompts(prompts)
        else:
            await self.client.set_prompts([prompts])

    async def update_prompts(self, prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]]):
        """Update the existing processing prompts.
        
        Args:
            prompts: Either a single prompt dictionary or a list of prompt dictionaries
        """
        if self.client is None:
            raise RuntimeError("Pipeline client not initialized. Call start() first.")
            
        if isinstance(prompts, list):
            await self.client.update_prompts(prompts)
        else:
            await self.client.update_prompts([prompts])

    async def warm_video(self, WARMUP_RUNS: int = 5, width: int = 512, height: int = 512):
        """Warm up the video processing pipeline."""
        await self.client.warm_video(WARMUP_RUNS, width, height)
        
    async def warm_audio(self, WARMUP_RUNS: int = 5, sample_rate: int = 48000, buffer_size: int = 48000):
        """Warm up the audio processing pipeline."""
        await self.client.warm_audio(WARMUP_RUNS, sample_rate, buffer_size)

    async def put_video_frame(self, frame: av.VideoFrame):
        """Queue a video frame for processing.
        
        Args:
            frame: The video frame to process
        """
        frame.side_data.input = self.video_preprocess(frame)
        frame.side_data.skipped = True
        self.client.put_video_input(frame)
        await self.video_incoming_frames.put(frame)

    async def put_audio_frame(self, frame: av.AudioFrame):
        """Queue an audio frame for processing.
        
        Args:
            frame: The audio frame to process
        """
        frame.side_data.input = self.audio_preprocess(frame)
        frame.side_data.skipped = True
        self.client.put_audio_input(frame)
        await self.audio_incoming_frames.put(frame)

    def video_preprocess(self, frame: av.VideoFrame) -> Union[torch.Tensor, np.ndarray]:
        """Preprocess a video frame before processing.
        
        Args:
            frame: The video frame to preprocess
            
        Returns:
            The preprocessed frame as a tensor or numpy array
        """
        frame_np = frame.to_ndarray(format="rgb24").astype(np.float32) / 255.0
        return torch.from_numpy(frame_np).unsqueeze(0)
    
    def audio_preprocess(self, frame: av.AudioFrame) -> Union[torch.Tensor, np.ndarray]:
        """Preprocess an audio frame before processing.
        
        Args:
            frame: The audio frame to preprocess
            
        Returns:
            The preprocessed frame as a tensor or numpy array
        """
        return frame.to_ndarray().ravel().reshape(-1, 2).mean(axis=1).astype(np.int16)
    
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
    
    async def get_processed_video_frame(self) -> av.VideoFrame:
        """Get the next processed video frame.
        
        Returns:
            The processed video frame
        """
        async with temporary_log_level("comfy", self._comfyui_inference_log_level):
            out_tensor = await self.client.get_video_output()
        frame = await self.video_incoming_frames.get()
        while frame.side_data.skipped:
            frame = await self.video_incoming_frames.get()

        processed_frame = self.video_postprocess(out_tensor)
        processed_frame.pts = frame.pts
        processed_frame.time_base = frame.time_base
        
        return processed_frame

    async def get_processed_audio_frame(self) -> av.AudioFrame:
        """Get the next processed audio frame.
        
        Returns:
            The processed audio frame
        """
        frame = await self.audio_incoming_frames.get()
        if frame.samples > len(self.processed_audio_buffer):
            async with temporary_log_level("comfy", self._comfyui_inference_log_level):
                out_tensor = await self.client.get_audio_output()
            self.processed_audio_buffer = np.concatenate([self.processed_audio_buffer, out_tensor])
        out_data = self.processed_audio_buffer[:frame.samples]
        self.processed_audio_buffer = self.processed_audio_buffer[frame.samples:]

        processed_frame = self.audio_postprocess(out_data)
        processed_frame.pts = frame.pts
        processed_frame.time_base = frame.time_base
        processed_frame.sample_rate = frame.sample_rate
        
        return processed_frame
    
    async def get_nodes_info(self) -> Dict[str, Any]:
        """Get information about all nodes in the current prompt including metadata.
        
        Returns:
            Dictionary containing node information
        """
        nodes_info = await self.client.get_available_nodes()
        return nodes_info
    
    async def cleanup(self):
        """Clean up resources used by the pipeline."""
        await self.stop()
    
        
    # Clear queues and move CUDA tensors to CPU before discarding
    def _unload_frame_tensors(self, frame):
        """Move CUDA tensors in frame to CPU."""
        if hasattr(frame, 'side_data') and hasattr(frame.side_data, 'input'):
            if isinstance(frame.side_data.input, torch.Tensor) and frame.side_data.input.is_cuda:
                frame.side_data.input = frame.side_data.input.cpu()

    def set_video_track(self, track):
        """Set the video track and start it if pipeline is running."""
        self.video_track = track
        if self._is_running and self._startup_event.is_set():
            asyncio.create_task(track.start())

    async def wait_for_startup(self):
        """Wait for pipeline to be fully initialized and ready."""
        await self._startup_event.wait()
