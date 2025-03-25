import av
import torch
import numpy as np
import asyncio
import logging

from typing import Any, Dict, Union, List
from comfystream.client_api import ComfyStreamClient
from comfystream import tensor_cache

WARMUP_RUNS = 5
logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, **kwargs):
        self.client = ComfyStreamClient(**kwargs)
        self.video_incoming_frames = asyncio.Queue()
        self.audio_incoming_frames = asyncio.Queue()

        self.processed_audio_buffer = np.array([], dtype=np.int16)

    async def warm_video(self):
        """Warm up the video pipeline with dummy frames"""
        logger.info("Warming up video pipeline...")
        
        # Create a properly formatted dummy frame (random color pattern)
        # Using standard tensor shape: BCHW [1, 3, 512, 512]
        tensor = torch.rand(1, 3, 512, 512)  # Random values in [0,1]
        
        # Create a dummy frame and attach the tensor as side_data
        dummy_frame = av.VideoFrame(width=512, height=512, format="rgb24")
        dummy_frame.side_data.input = tensor
        
        # Process a few frames for warmup
        for i in range(WARMUP_RUNS):
            logger.info(f"Video warmup iteration {i+1}/{WARMUP_RUNS}")
            self.client.put_video_input(dummy_frame)
            await self.client.get_video_output()
        
        logger.info("Video pipeline warmup complete")

    async def warm_audio(self):
        dummy_frame = av.AudioFrame()
        dummy_frame.side_data.input = np.random.randint(-32768, 32767, int(48000 * 0.5), dtype=np.int16)   # TODO: adds a lot of delay if it doesn't match the buffer size, is warmup needed?
        dummy_frame.sample_rate = 48000

        for _ in range(WARMUP_RUNS):
            self.client.put_audio_input(dummy_frame)
            await self.client.get_audio_output()

    async def set_prompts(self, prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]]):
        if isinstance(prompts, list):
            await self.client.set_prompts(prompts)
        else:
            await self.client.set_prompts([prompts])

    async def update_prompts(self, prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]]):
        if isinstance(prompts, list):
            await self.client.update_prompts(prompts)
        else:
            await self.client.update_prompts([prompts])

    async def put_video_frame(self, frame: av.VideoFrame):
        frame.side_data.input = self.video_preprocess(frame)
        frame.side_data.skipped = False # Different from LoadTensor, we don't skip frames here
        self.client.put_video_input(frame)
        await self.video_incoming_frames.put(frame)

    async def put_audio_frame(self, frame: av.AudioFrame):
        frame.side_data.input = self.audio_preprocess(frame)
        frame.side_data.skipped = False
        self.client.put_audio_input(frame)
        await self.audio_incoming_frames.put(frame)

    def audio_preprocess(self, frame: av.AudioFrame) -> Union[torch.Tensor, np.ndarray]:
        return frame.to_ndarray().ravel().reshape(-1, 2).mean(axis=1).astype(np.int16)
    
    # Works with ComfyUI Native
    def video_preprocess(self, frame: av.VideoFrame) -> Union[torch.Tensor, np.ndarray]:
        frame_np = frame.to_ndarray(format="rgb24").astype(np.float32) / 255.0
        return torch.from_numpy(frame_np).unsqueeze(0)
    
    ''' Converts HWC format (height, width, channels) to VideoFrame.
    def video_postprocess(self, output: Union[torch.Tensor, np.ndarray]) -> av.VideoFrame:
        return av.VideoFrame.from_ndarray(
            (output * 255.0).clamp(0, 255).to(dtype=torch.uint8).squeeze(0).cpu().numpy()
        )
    '''

    '''Converts BCHW tensor [1,3,H,W] to VideoFrame. Assumes values are in range [0,1].'''
    def video_postprocess(self, output: Union[torch.Tensor, np.ndarray]) -> av.VideoFrame:
        return av.VideoFrame.from_ndarray(
            (output.squeeze(0).permute(1, 2, 0) * 255.0)
            .clamp(0, 255)
            .to(dtype=torch.uint8)
            .cpu()
            .numpy(),
            format='rgb24'
        )

    def audio_postprocess(self, output: Union[torch.Tensor, np.ndarray]) -> av.AudioFrame:
        return av.AudioFrame.from_ndarray(np.repeat(output, 2).reshape(1, -1))

    async def get_processed_video_frame(self):
        """Get processed video frame from output queue and match it with input frame"""
        try:
            # Get the frame from the incoming queue first
            frame = await self.video_incoming_frames.get()
            
            while frame.side_data.skipped:
                frame = await self.video_incoming_frames.get()

            # Get the processed frame from the output queue
            logger.info("Getting video output")
            out_tensor = await self.client.get_video_output()
            
            # If there are more frames in the output queue, drain them to get the most recent
            # This helps with synchronization when processing is faster than display
            while not tensor_cache.image_outputs.empty():
                try:
                    newer_tensor = await asyncio.wait_for(self.client.get_video_output(), 0.01)
                    out_tensor = newer_tensor  # Use the most recent frame
                    logger.info("Using more recent frame from output queue")
                except asyncio.TimeoutError:
                    break
                
            logger.info(f"Received output tensor with shape: {out_tensor.shape if hasattr(out_tensor, 'shape') else 'unknown'}")
            
            # Process the output tensor
            processed_frame = self.video_postprocess(out_tensor)
            processed_frame.pts = frame.pts
            processed_frame.time_base = frame.time_base
            
            return processed_frame
            
        except Exception as e:
            logger.error(f"Error in get_processed_video_frame: {str(e)}")
            # Create a black frame as fallback
            black_frame = av.VideoFrame(width=512, height=512, format='rgb24')
            return black_frame

    async def get_processed_audio_frame(self):
        # TODO: make it generic to support purely generative audio cases and also add frame skipping
        frame = await self.audio_incoming_frames.get()
        if frame.samples > len(self.processed_audio_buffer):
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
        """Get information about all nodes in the current prompt including metadata."""
        nodes_info = await self.client.get_available_nodes()
        return nodes_info
    
    async def cleanup(self):
        await self.client.cleanup()