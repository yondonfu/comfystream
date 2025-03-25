import av
import torch
import numpy as np
import asyncio
import logging
import time
import random
from collections import deque

from typing import Any, Dict, Union, List, Optional, Deque
from comfystream.client_api import ComfyStreamClient
from config import ComfyConfig

WARMUP_RUNS = 5
logger = logging.getLogger(__name__)


class MultiServerPipeline:
    def __init__(self, config_path: Optional[str] = None, **kwargs):
        # Load server configurations
        self.config = ComfyConfig(config_path)
        self.servers = self.config.get_servers()
        
        # Create client for each server
        self.clients = []
        for server_config in self.servers:
            client_kwargs = kwargs.copy()
            client_kwargs.update(server_config)
            self.clients.append(ComfyStreamClient(**client_kwargs))
        
        logger.info(f"Initialized {len(self.clients)} ComfyUI clients")
        
        self.video_incoming_frames = asyncio.Queue()
        self.audio_incoming_frames = asyncio.Queue()
        
        # Queue for processed frames from all clients
        self.processed_video_frames = asyncio.Queue()
        
        # Track which client gets each frame (round-robin)
        self.current_client_index = 0
        self.client_frame_mapping = {}  # Maps frame_id -> client_index
        
        # Buffer to store frames in order of original pts
        self.frame_output_buffer: Deque = deque()
        
        # Audio processing
        self.processed_audio_buffer = np.array([], dtype=np.int16)
        self.last_frame_time = 0

        # Frame rate limiting
        self.min_frame_interval = 1/30  # Limit to 30 FPS
        
        # Create background task for collecting processed frames
        self.running = True
        self.collector_task = asyncio.create_task(self._collect_processed_frames())

    async def _collect_processed_frames(self):
        """Background task to collect processed frames from all clients"""
        try:
            while self.running:
                for i, client in enumerate(self.clients):
                    try:
                        # Non-blocking check if client has output ready
                        if hasattr(client, '_prompt_id') and client._prompt_id is not None:
                            # Get frame without waiting
                            try:
                                # Use wait_for with small timeout to avoid blocking
                                out_tensor = await asyncio.wait_for(
                                    client.get_video_output(), 
                                    timeout=0.01
                                )
                                
                                # Find which original frame this corresponds to
                                # (using a simple approach here - could be improved)
                                # In real implementation, need to track which frames went to which client
                                frame_ids = [frame_id for frame_id, client_idx in 
                                          self.client_frame_mapping.items() if client_idx == i]
                                
                                if frame_ids:
                                    # Use the oldest frame ID for this client
                                    frame_id = min(frame_ids)
                                    # Store the processed tensor along with original frame ID for ordering
                                    await self.processed_video_frames.put((frame_id, out_tensor))
                                    # Remove the mapping
                                    self.client_frame_mapping.pop(frame_id, None)
                                    logger.info(f"Collected processed frame from client {i}, frame_id: {frame_id}")
                            except asyncio.TimeoutError:
                                # No frame ready yet, continue
                                pass
                    except Exception as e:
                        logger.error(f"Error collecting frame from client {i}: {e}")
                
                # Small sleep to avoid CPU spinning
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logger.info("Frame collector task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in frame collector: {e}")

    async def warm_video(self):
        """Warm up the video pipeline with dummy frames for each client"""
        logger.info("Warming up video pipeline...")
        
        # Create a properly formatted dummy frame
        tensor = torch.rand(1, 3, 512, 512)  # Random values in [0,1]
        dummy_frame = av.VideoFrame(width=512, height=512, format="rgb24")
        dummy_frame.side_data.input = tensor
        
        # Warm up each client
        warmup_tasks = []
        for i, client in enumerate(self.clients):
            warmup_tasks.append(self._warm_client_video(client, i, dummy_frame))
            
        # Wait for all warmup tasks to complete
        await asyncio.gather(*warmup_tasks)
        logger.info("Video pipeline warmup complete")
    
    async def _warm_client_video(self, client, client_index, dummy_frame):
        """Warm up a single client"""
        logger.info(f"Warming up client {client_index}")
        for i in range(WARMUP_RUNS):
            logger.info(f"Client {client_index} warmup iteration {i+1}/{WARMUP_RUNS}")
            client.put_video_input(dummy_frame)
            try:
                await asyncio.wait_for(client.get_video_output(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for warmup frame from client {client_index}")
            except Exception as e:
                logger.error(f"Error warming client {client_index}: {e}")

    async def warm_audio(self):
        # For now, only use the first client for audio
        if not self.clients:
            logger.warning("No clients available for audio warmup")
            return
            
        dummy_frame = av.AudioFrame()
        dummy_frame.side_data.input = np.random.randint(-32768, 32767, int(48000 * 0.5), dtype=np.int16)
        dummy_frame.sample_rate = 48000

        for _ in range(WARMUP_RUNS):
            self.clients[0].put_audio_input(dummy_frame)
            await self.clients[0].get_audio_output()

    async def set_prompts(self, prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]]):
        """Set the same prompts for all clients"""
        if isinstance(prompts, dict):
            prompts = [prompts]
            
        # Set prompts for each client
        tasks = []
        for client in self.clients:
            tasks.append(client.set_prompts(prompts))
            
        await asyncio.gather(*tasks)
        logger.info(f"Set prompts for {len(self.clients)} clients")

    async def update_prompts(self, prompts: Union[Dict[Any, Any], List[Dict[Any, Any]]]):
        """Update prompts for all clients"""
        if isinstance(prompts, dict):
            prompts = [prompts]
            
        # Update prompts for each client
        tasks = []
        for client in self.clients:
            tasks.append(client.update_prompts(prompts))
            
        await asyncio.gather(*tasks)
        logger.info(f"Updated prompts for {len(self.clients)} clients")

    async def put_video_frame(self, frame: av.VideoFrame):
        """Distribute video frames among clients using round-robin"""
        current_time = time.time()
        if current_time - self.last_frame_time < self.min_frame_interval:
            return  # Skip frame if too soon
            
        self.last_frame_time = current_time
        
        # Generate a unique frame ID
        frame_id = int(time.time() * 1000000)  # Microseconds as ID
        frame.side_data.frame_id = frame_id
        
        # Preprocess the frame
        frame.side_data.input = self.video_preprocess(frame)
        frame.side_data.skipped = False
        
        # Select the next client in round-robin fashion
        client_index = self.current_client_index
        self.current_client_index = (self.current_client_index + 1) % len(self.clients)
        
        # Store mapping of which client is processing this frame
        self.client_frame_mapping[frame_id] = client_index
        
        # Send frame to the selected client
        self.clients[client_index].put_video_input(frame)
        
        # Also add to the incoming queue for reference
        await self.video_incoming_frames.put(frame)
        
        logger.info(f"Sent frame {frame_id} to client {client_index}")

    async def put_audio_frame(self, frame: av.AudioFrame):
        # For now, only use the first client for audio
        if not self.clients:
            return
            
        frame.side_data.input = self.audio_preprocess(frame)
        frame.side_data.skipped = False
        self.clients[0].put_audio_input(frame)
        await self.audio_incoming_frames.put(frame)

    def audio_preprocess(self, frame: av.AudioFrame) -> Union[torch.Tensor, np.ndarray]:
        return frame.to_ndarray().ravel().reshape(-1, 2).mean(axis=1).astype(np.int16)
    
    def video_preprocess(self, frame: av.VideoFrame) -> Union[torch.Tensor, np.ndarray]:
        # Convert directly to tensor, avoiding intermediate numpy array when possible
        if hasattr(frame, 'to_tensor'):
            tensor = frame.to_tensor()
        else:
            # If direct tensor conversion not available, use numpy
            frame_np = frame.to_ndarray(format="rgb24")
            tensor = torch.from_numpy(frame_np)
        
        # Normalize to [0,1] range and add batch dimension
        return tensor.float().div(255.0).unsqueeze(0)

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
        try:
            # Get the frame from the incoming queue first to maintain timing
            frame = await self.video_incoming_frames.get()
            
            # Skip frames if we're falling behind
            while not self.video_incoming_frames.empty():
                # Get newer frame and mark old one as skipped
                frame.side_data.skipped = True
                frame = await self.video_incoming_frames.get()
                logger.info("Skipped older frame to catch up")
            
            # Get the processed frame from our output queue
            frame_id, out_tensor = await self.processed_video_frames.get()
            
            # Process the frame
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
        # Only use the first client for audio
        if not self.clients:
            logger.warning("No clients available for audio processing")
            return av.AudioFrame(format='s16', layout='mono', samples=1024)
            
        frame = await self.audio_incoming_frames.get()
        if frame.samples > len(self.processed_audio_buffer):
            out_tensor = await self.clients[0].get_audio_output()
            self.processed_audio_buffer = np.concatenate([self.processed_audio_buffer, out_tensor])
        out_data = self.processed_audio_buffer[:frame.samples]
        self.processed_audio_buffer = self.processed_audio_buffer[frame.samples:]

        processed_frame = self.audio_postprocess(out_data)
        processed_frame.pts = frame.pts
        processed_frame.time_base = frame.time_base
        processed_frame.sample_rate = frame.sample_rate
        
        return processed_frame
    
    async def get_nodes_info(self) -> Dict[str, Any]:
        """Get information about nodes from the first client"""
        if not self.clients:
            return {}
        return await self.clients[0].get_available_nodes()
    
    async def cleanup(self):
        """Clean up all clients and background tasks"""
        self.running = False
        
        # Cancel collector task
        if hasattr(self, 'collector_task') and not self.collector_task.done():
            self.collector_task.cancel()
            try:
                await self.collector_task
            except asyncio.CancelledError:
                pass
        
        # Clean up all clients
        cleanup_tasks = []
        for client in self.clients:
            cleanup_tasks.append(client.cleanup())
            
        await asyncio.gather(*cleanup_tasks)
        logger.info("All clients cleaned up")


# For backwards compatibility, maintain the original Pipeline name
Pipeline = MultiServerPipeline