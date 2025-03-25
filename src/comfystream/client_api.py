import asyncio
import json
import uuid
import websockets
import base64
import aiohttp
import logging
import torch
import numpy as np
from io import BytesIO
from PIL import Image
from typing import List, Dict, Any, Optional, Union
import random
import time

from comfystream import tensor_cache
from comfystream.utils_api import convert_prompt

logger = logging.getLogger(__name__)

class ComfyStreamClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8198, **kwargs):
        """
        Initialize the ComfyStream client to use the ComfyUI API.
        
        Args:
            host: The hostname or IP address of the ComfyUI server
            port: The port number of the ComfyUI server
            **kwargs: Additional configuration parameters
        """
        self.host = host
        self.port = port
        self.server_address = f"ws://{host}:{port}/ws"
        self.api_base_url = f"http://{host}:{port}/api"
        self.client_id = kwargs.get('client_id', str(uuid.uuid4()))
        self.api_version = kwargs.get('api_version', "1.0.0")
        self.ws = None
        self.current_prompts = []
        self.running_prompts = {}
        self.cleanup_lock = asyncio.Lock()
        
        # WebSocket connection
        self._ws_listener_task = None
        self.execution_complete_event = asyncio.Event()
        self.execution_started = False
        self._prompt_id = None
        
        # Configure logging
        if 'log_level' in kwargs:
            logger.setLevel(kwargs['log_level'])
        
        # Enable debug mode
        self.debug = kwargs.get('debug', True)

        logger.info(f"ComfyStreamClient initialized with host: {host}, port: {port}, client_id: {self.client_id}")
    
    async def set_prompts(self, prompts: List[Dict]):
        """Set prompts and run them (compatible with original interface)"""
        # Convert prompts (this already randomizes seeds, but we'll enhance it)
        self.current_prompts = [convert_prompt(prompt) for prompt in prompts]
        
        # Create tasks for each prompt
        for idx in range(len(self.current_prompts)):
            task = asyncio.create_task(self.run_prompt(idx))
            self.running_prompts[idx] = task
            
        logger.info(f"Set {len(self.current_prompts)} prompts for execution")
    
    async def update_prompts(self, prompts: List[Dict]):
        """Update existing prompts (compatible with original interface)"""
        if len(prompts) != len(self.current_prompts):
            raise ValueError(
                "Number of updated prompts must match the number of currently running prompts."
            )
        self.current_prompts = [convert_prompt(prompt) for prompt in prompts]
        logger.info(f"Updated {len(self.current_prompts)} prompts")
    
    async def run_prompt(self, prompt_index: int):
        """Run a prompt continuously, processing new frames as they arrive"""
        logger.info(f"Running prompt {prompt_index}")
        
        # Make sure WebSocket is connected
        await self._connect_websocket()
        
        # Always set execution complete at start to allow first frame to be processed
        self.execution_complete_event.set()
        
        try:
            while True:
                # Wait until we have tensor data available before sending prompt
                if tensor_cache.image_inputs.empty():
                    await asyncio.sleep(0.01)  # Reduced sleep time for faster checking
                    continue
                
                # Clear event before sending a new prompt
                if self.execution_complete_event.is_set():
                    # Reset execution state for next frame
                    self.execution_complete_event.clear()
                    
                    # Queue the prompt with the current frame
                    await self._execute_prompt(prompt_index)
                    
                    # Wait for execution completion with timeout
                    try:
                        # logger.info("Waiting for execution to complete (max 10 seconds)...")
                        await asyncio.wait_for(self.execution_complete_event.wait(), timeout=10.0)
                        # logger.info("Execution complete, ready for next frame")
                    except asyncio.TimeoutError:
                        logger.error("Timeout waiting for execution, forcing continuation")
                        self.execution_complete_event.set()
                else:
                    # If execution is not complete, check again shortly
                    await asyncio.sleep(0.01)  # Short sleep to prevent CPU spinning
                
        except asyncio.CancelledError:
            logger.info(f"Prompt {prompt_index} execution cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in run_prompt: {str(e)}")
            raise
    
    async def _connect_websocket(self):
        """Connect to the ComfyUI WebSocket endpoint"""
        try:
            if self.ws is not None and self.ws.open:
                return self.ws

            # Close existing connection if any
            if self.ws is not None:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
            
            logger.info(f"Connecting to WebSocket at {self.server_address}?clientId={self.client_id}")
            
            # Set a reasonable timeout for connection
            websocket_timeout = 10.0  # seconds
            
            try:
                # Connect with proper error handling
                self.ws = await websockets.connect(
                    f"{self.server_address}?clientId={self.client_id}",
                    ping_interval=5,
                    ping_timeout=10,
                    close_timeout=5,
                    max_size=None,  # No limit on message size
                    ssl=None
                )
                
                logger.info("WebSocket connected successfully")
                
                # Start the listener task if not already running
                if self._ws_listener_task is None or self._ws_listener_task.done():
                    self._ws_listener_task = asyncio.create_task(self._ws_listener())
                    logger.info("Started WebSocket listener task")
                    
                return self.ws
                
            except (websockets.exceptions.WebSocketException, ConnectionError, OSError) as e:
                logger.error(f"WebSocket connection error: {e}")
                self.ws = None
                # Signal execution complete to prevent hanging if connection fails
                self.execution_complete_event.set()
                # Retry after a delay
                await asyncio.sleep(1)
                return await self._connect_websocket()
                
        except Exception as e:
            logger.error(f"Unexpected error in _connect_websocket: {e}")
            self.ws = None
            # Signal execution complete to prevent hanging
            self.execution_complete_event.set()
            return None
    
    async def _ws_listener(self):
        """Listen for WebSocket messages and process them"""
        try:
            logger.info(f"WebSocket listener started")
            while True:
                if self.ws is None:
                    try:
                        await self._connect_websocket()
                    except Exception as e:
                        logger.error(f"Error connecting to WebSocket: {e}")
                        await asyncio.sleep(1)
                        continue
                
                try:
                    # Receive and process messages
                    message = await self.ws.recv()

                    if isinstance(message, str):
                        # Process JSON messages
                        await self._handle_text_message(message)
                    else:
                        # Handle binary data - likely image preview or tensor data
                        await self._handle_binary_message(message)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed")
                    self.ws = None
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error in WebSocket listener: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("WebSocket listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in WebSocket listener: {e}")
    
    async def _handle_text_message(self, message: str):
        """Process text (JSON) messages from the WebSocket"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")

            # logger.info(f"Received message type: {message_type}")
            
            # Handle different message types
            if message_type == "status":
                pass
                '''
                # Status message with comfy_ui's queue information
                queue_remaining = data.get("data", {}).get("queue_remaining", 0)
                exec_info = data.get("data", {}).get("exec_info", {})
                if queue_remaining == 0 and not exec_info:
                    logger.info("Queue empty, no active execution")
                else:
                    logger.info(f"Queue status: {queue_remaining} items remaining")
                '''
                
            elif message_type == "progress":
                if "data" in data and "value" in data["data"]:
                    progress = data["data"]["value"]
                    max_value = data["data"].get("max", 100)
                    # Log the progress for debugging
                    # logger.info(f"Progress: {progress}/{max_value}")
                
            elif message_type == "execution_start":
                self.execution_started = True
                if "data" in data and "prompt_id" in data["data"]:
                    self._prompt_id = data["data"]["prompt_id"]
                    # logger.info(f"Execution started for prompt {self._prompt_id}")
                
            elif message_type == "executing":
                self.execution_started = True
                if "data" in data:
                    if "prompt_id" in data["data"]:
                        self._prompt_id = data["data"]["prompt_id"]
                    if "node" in data["data"]:
                        node_id = data["data"]["node"]
                        # logger.info(f"Executing node: {node_id}")
            
            elif message_type in ["execution_cached", "execution_error", "execution_complete", "execution_interrupted"]:
                # logger.info(f"{message_type} message received for prompt {self._prompt_id}")
                # self.execution_started = False
                
                # Always signal completion for these terminal states
                # self.execution_complete_event.set()
                # logger.info(f"Set execution_complete_event from {message_type}")
                pass
            
            elif message_type == "executed":
                # This is sent when a node is completely done
                if "data" in data and "node_id" in data["data"]:
                    node_id = data["data"]["node_id"]
                    logger.info(f"Node execution complete: {node_id}")
                    
                    # Check if this is our SaveTensorAPI node
                    if "SaveTensorAPI" in str(node_id):
                        logger.info("SaveTensorAPI node executed, checking for tensor data")
                        # The binary data should come separately via websocket
                    
                    # If we've been running for too long without tensor data, force completion
                    elif self.execution_started and not self.execution_complete_event.is_set():
                        # Check if this was the last node
                        if data.get("data", {}).get("remaining", 0) == 0:
                            # logger.info("All nodes executed but no tensor data received, forcing completion")
                            # self.execution_complete_event.set()
                            pass
            
            elif message_type == "executed_node" and "output" in data.get("data", {}):
                node_id = data.get("data", {}).get("node_id")
                output_data = data.get("data", {}).get("output", {})
                prompt_id = data.get("data", {}).get("prompt_id", "unknown")
                
                logger.info(f"Node {node_id} executed in prompt {prompt_id}")
                
                '''
                # Check if this is from ETN_SendImageWebSocket node
                if "ui" in output_data and "images" in output_data["ui"]:
                    images_info = output_data["ui"]["images"]
                    logger.info(f"Found image output from ETN_SendImageWebSocket in node {node_id}")
                    
                    # Images will be received via binary websocket messages after this event
                    # The binary handler will take care of them
                    pass
                
                # Keep existing handling for tensor data
                elif "ui" in output_data and "tensor" in output_data["ui"]:
                    tensor_info = output_data["ui"]["tensor"]
                    tensor_id = tensor_info.get("tensor_id", "unknown")
                    logger.info(f"Found tensor data with ID: {tensor_id} in node {node_id}")
                    
                    # Decode the tensor data
                    tensor_data = await self._decode_tensor_data(tensor_info)
                    if tensor_data is not None:
                        # Add to output queue without waiting to unblock event loop
                        tensor_cache.image_outputs.put_nowait(tensor_data)
                        logger.info(f"Added tensor to output queue, shape: {tensor_data.shape}")
                        
                        # IMPORTANT: Immediately signal that we can proceed with the next frame
                        # when we receive tensor data, don't wait
                        logger.info("Received tensor data, immediately signaling execution complete")
                        self.execution_complete_event.set()
                        logger.info("Set execution_complete_event after processing tensor data")
                    else:
                        logger.error("Failed to decode tensor data")
                        # Signal completion even if decoding failed to prevent hanging
                        self.execution_complete_event.set()
                '''
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message: {message[:100]}...")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            # Signal completion on error to prevent hanging
            self.execution_complete_event.set()
    
    async def _handle_binary_message(self, binary_data):
        """Process binary messages from the WebSocket"""
        try:
            # Early return if message is too short
            if len(binary_data) <= 8:
                self.execution_complete_event.set()
                return
            
            # Extract header data only when needed
            event_type = int.from_bytes(binary_data[:4], byteorder='little')
            format_type = int.from_bytes(binary_data[4:8], byteorder='little')
            data = binary_data[8:]
            
            # Quick check for image format
            is_image = data[:2] in [b'\xff\xd8', b'\x89\x50']
            if not is_image:
                self.execution_complete_event.set()
                return
            
            # Process image data directly
            try:
                img = Image.open(BytesIO(data))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                    
                with torch.no_grad():
                    tensor = torch.from_numpy(np.array(img)).float().permute(2, 0, 1).unsqueeze(0) / 255.0
                
                # Add to output queue without waiting
                tensor_cache.image_outputs.put_nowait(tensor)
                self.execution_complete_event.set()
                
            except Exception as img_error:
                logger.error(f"Error processing image: {img_error}")
                self.execution_complete_event.set()
                
        except Exception as e:
            logger.error(f"Error handling binary message: {e}")
            self.execution_complete_event.set()
    
    async def _execute_prompt(self, prompt_index: int):
        try:
            # Get the prompt to execute
            prompt = self.current_prompts[prompt_index]
            
            # Check if we have a frame waiting to be processed
            if not tensor_cache.image_inputs.empty():
                # logger.info("Found tensor in input queue, preparing for API")
                # Get the most recent frame only
                frame_or_tensor = None
                while not tensor_cache.image_inputs.empty():
                    frame_or_tensor = tensor_cache.image_inputs.get_nowait()
                
                # Find ETN_LoadImageBase64 nodes first
                load_image_nodes = []
                for node_id, node in prompt.items():
                    if isinstance(node, dict) and node.get("class_type") in ["ETN_LoadImageBase64", "LoadImageBase64"]:
                        load_image_nodes.append(node_id)
                
                if not load_image_nodes:
                    logger.warning("No LoadImageBase64 nodes found in the prompt")
                    self.execution_complete_event.set()
                    return
                
                # Process the tensor ONLY if we have nodes to send it to
                try:
                    # Get the actual tensor data - handle different input types
                    tensor = None
                    
                    # Handle different input types efficiently
                    if hasattr(frame_or_tensor, 'side_data') and hasattr(frame_or_tensor.side_data, 'input'):
                        tensor = frame_or_tensor.side_data.input
                    elif isinstance(frame_or_tensor, torch.Tensor):
                        tensor = frame_or_tensor
                    elif isinstance(frame_or_tensor, np.ndarray):
                        tensor = torch.from_numpy(frame_or_tensor).float()
                    elif hasattr(frame_or_tensor, 'to_ndarray'):
                        frame_np = frame_or_tensor.to_ndarray(format="rgb24").astype(np.float32) / 255.0
                        tensor = torch.from_numpy(frame_np).unsqueeze(0)
                    
                    if tensor is None:
                        logger.error("Failed to get valid tensor data from input")
                        self.execution_complete_event.set()
                        return
                    
                    # Process tensor format only once
                    with torch.no_grad():
                        tensor = tensor.detach().cpu().float()
                        
                        # Handle different formats
                        if len(tensor.shape) == 4:  # BCHW format (batch)
                            tensor = tensor[0]  # Take first image from batch
                        
                        # Ensure it's in CHW format
                        if len(tensor.shape) == 3 and tensor.shape[2] == 3:  # HWC format
                            tensor = tensor.permute(2, 0, 1)  # Convert to CHW
                        
                        # Convert to PIL image for base64 ONLY ONCE
                        tensor_np = (tensor.permute(1, 2, 0) * 255).clamp(0, 255).numpy().astype(np.uint8)
                        img = Image.fromarray(tensor_np)
                        
                        # Convert to base64 ONCE for all nodes
                        buffer = BytesIO()
                        img.save(buffer, format="PNG")
                        buffer.seek(0)
                        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    # Update all nodes with the SAME base64 string
                    timestamp = int(time.time() * 1000)
                    for node_id in load_image_nodes:
                        prompt[node_id]["inputs"]["image"] = img_base64
                        prompt[node_id]["inputs"]["_timestamp"] = timestamp
                        # Use timestamp as cache buster instead of random number
                        prompt[node_id]["inputs"]["_cache_buster"] = str(timestamp)
                
                except Exception as e:
                    logger.error(f"Error converting tensor to base64: {e}")
                    self.execution_complete_event.set()
                    return
                
                # Execute the prompt via API
                async with aiohttp.ClientSession() as session:
                    api_url = f"{self.api_base_url}/prompt"
                    payload = {
                        "prompt": prompt,
                        "client_id": self.client_id
                    }
                    
                    async with session.post(api_url, json=payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            self._prompt_id = result.get("prompt_id")
                            self.execution_started = True
                        else:
                            error_text = await response.text()
                            logger.error(f"Error queueing prompt: {response.status} - {error_text}")
                            self.execution_complete_event.set()
            else:
                logger.info("No tensor in input queue, skipping prompt execution")
                self.execution_complete_event.set()
                
        except Exception as e:
            logger.error(f"Error executing prompt: {e}")
            self.execution_complete_event.set()
    
    async def _send_tensor_via_websocket(self, tensor):
        """Send tensor data via the websocket connection"""
        try:
            if self.ws is None:
                logger.error("WebSocket not connected, cannot send tensor")
                self.execution_complete_event.set()  # Prevent hanging
                return
            
            # Convert the tensor to image format for sending
            if isinstance(tensor, np.ndarray):
                tensor = torch.from_numpy(tensor).float()
            
            # Ensure on CPU and correct format
            tensor = tensor.detach().cpu().float()
            
            # Prepare binary data
            if len(tensor.shape) == 4:  # BCHW format (batch of images)
                if tensor.shape[0] > 1:
                    logger.info(f"Taking first image from batch of {tensor.shape[0]}")
                tensor = tensor[0]  # Take first image if batch
            
            # Ensure CHW format (3 channels)
            if len(tensor.shape) == 3:
                if tensor.shape[0] != 3 and tensor.shape[2] == 3:  # HWC format
                    tensor = tensor.permute(2, 0, 1)  # Convert to CHW
                elif tensor.shape[0] != 3:
                    logger.warning(f"Tensor doesn't have 3 channels: {tensor.shape}. Creating standard tensor.")
                    # Create a standard RGB tensor
                    tensor = torch.zeros(3, 512, 512)
            else:
                logger.warning(f"Tensor has unexpected shape: {tensor.shape}. Creating standard tensor.")
                # Create a standard RGB tensor
                tensor = torch.zeros(3, 512, 512)
            
            # Check tensor dimensions and log detailed info
            logger.info(f"Original tensor for WS: shape={tensor.shape}, min={tensor.min().item():.4f}, max={tensor.max().item():.4f}")
            
            # Always ensure consistent 512x512 dimensions
            '''
            if tensor.shape[1] != 512 or tensor.shape[2] != 512:
                logger.info(f"Resizing tensor from {tensor.shape} to standard 512x512")
                import torch.nn.functional as F
                tensor = tensor.unsqueeze(0)  # Add batch dimension for interpolate
                tensor = F.interpolate(tensor, size=(512, 512), mode='bilinear', align_corners=False)
                tensor = tensor.squeeze(0)  # Remove batch dimension after resize
            '''

            # Check for NaN or Inf values
            if torch.isnan(tensor).any() or torch.isinf(tensor).any():
                logger.warning("Tensor contains NaN or Inf values! Replacing with zeros.")
                tensor = torch.nan_to_num(tensor, nan=0.0, posinf=1.0, neginf=0.0)
            
            # Convert to image (HWC for PIL)
            tensor_np = (tensor.permute(1, 2, 0) * 255).clamp(0, 255).numpy().astype(np.uint8)
            img = Image.fromarray(tensor_np)
            
            logger.info(f"Converted to PIL image with dimensions: {img.size}")
            
            # Convert to PNG 
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            img_bytes = buffer.getvalue()
            
            # CRITICAL FIX: We need to send the binary data with a proper node ID prefix
            # LoadTensorAPI node expects this header format to identify the target node
            # The first 4 bytes are the message type (3 for binary tensor) and the next 4 are the node ID
            # Since we don't know the exact node ID, we'll use a generic one that will be interpreted as 
            # "send this to the currently waiting LoadTensorAPI node"
            
            # Build header (8 bytes total)
            header = bytearray()
            # Message type 3 (custom binary tensor data)
            header.extend((3).to_bytes(4, byteorder='little'))
            # Generic node ID (0 means "send to whatever node is waiting")
            header.extend((0).to_bytes(4, byteorder='little'))
            
            # Combine header and image data
            full_data = header + img_bytes
            
            # Send binary data via websocket
            await self.ws.send(full_data)
            logger.info(f"Sent tensor as PNG image via websocket with proper header, size: {len(full_data)} bytes, image dimensions: {img.size}")
            
        except Exception as e:
            logger.error(f"Error sending tensor via websocket: {e}")
            
            # Signal execution complete in case of error
            self.execution_complete_event.set()
    
    async def cleanup(self):
        """Clean up resources"""
        async with self.cleanup_lock:
            # Cancel all running tasks
            for task in self.running_prompts.values():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            self.running_prompts.clear()
            
            # Close WebSocket connection
            if self.ws:
                try:
                    await self.ws.close()
                except Exception as e:
                    logger.error(f"Error closing WebSocket: {e}")
                self.ws = None
            
            # Cancel WebSocket listener task
            if self._ws_listener_task and not self._ws_listener_task.done():
                self._ws_listener_task.cancel()
                try:
                    await self._ws_listener_task
                except asyncio.CancelledError:
                    pass
                self._ws_listener_task = None
            
            await self.cleanup_queues()
            logger.info("Client cleanup complete")
    
    async def cleanup_queues(self):
        """Clean up tensor queues"""
        while not tensor_cache.image_inputs.empty():
            tensor_cache.image_inputs.get()

        while not tensor_cache.audio_inputs.empty():
            tensor_cache.audio_inputs.get()

        while tensor_cache.image_outputs.qsize() > 0:
            try:
                await tensor_cache.image_outputs.get()
            except:
                pass

        while tensor_cache.audio_outputs.qsize() > 0:
            try:
                await tensor_cache.audio_outputs.get()
            except:
                pass
        
        logger.info("Tensor queues cleared")
    
    def put_video_input(self, tensor: Union[torch.Tensor, np.ndarray]):
        """
        Put a video TENSOR into the tensor cache for processing.
        
        Args:
            tensor: Video frame as a tensor (or numpy array)
        """
        try:
            # Only remove one frame if the queue is full (like in client.py)
            if tensor_cache.image_inputs.full():
                tensor_cache.image_inputs.get_nowait()
            
            # Ensure tensor is detached if it's a torch tensor
            if isinstance(tensor, torch.Tensor):
                tensor = tensor.detach()
                
            tensor_cache.image_inputs.put(tensor)
            
        except Exception as e:
            logger.error(f"Error in put_video_input: {e}")
    
    def put_audio_input(self, frame):
        """Put audio frame into tensor cache"""
        tensor_cache.audio_inputs.put(frame)
        
    async def get_video_output(self):
        """Get processed video frame from tensor cache"""
        # logger.info("Waiting for processed tensor from output queue")
        result = await tensor_cache.image_outputs.get()
        # logger.info(f"Got processed tensor from output queue: shape={result.shape if hasattr(result, 'shape') else 'unknown'}")
        return result
    
    async def get_audio_output(self):
        """Get processed audio frame from tensor cache"""
        return await tensor_cache.audio_outputs.get()
        
    async def get_available_nodes(self):
        """Get metadata and available nodes info for current prompts"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base_url}/object_info"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Format node info similar to the embedded client response
                        all_prompts_nodes_info = {}
                        
                        for prompt_index, prompt in enumerate(self.current_prompts):
                            nodes_info = {}
                            
                            for node_id, node in prompt.items():
                                class_type = node.get('class_type')
                                if class_type:
                                    nodes_info[node_id] = {
                                        'class_type': class_type,
                                        'inputs': {}
                                    }
                                    
                                    if 'inputs' in node:
                                        for input_name, input_value in node['inputs'].items():
                                            nodes_info[node_id]['inputs'][input_name] = {
                                                'value': input_value,
                                                'type': 'unknown'  # We don't have type information
                                            }
                            
                            all_prompts_nodes_info[prompt_index] = nodes_info
                        
                        return all_prompts_nodes_info
                        
                    else:
                        logger.error(f"Error getting node info: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error getting node info: {str(e)}")
            return {}