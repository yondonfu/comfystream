import threading
import time
import numpy as np
import cv2
import av
from typing import Optional

class FrameBuffer:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FrameBuffer()
        return cls._instance
    
    def __init__(self):
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.last_update_time = 0
        self.quality = 70  # JPEG quality (0-100)
        
    def update_frame(self, frame):
        """Update the current frame in the buffer"""
        with self.frame_lock:
            # Convert frame to numpy array if it's an av.VideoFrame
            if isinstance(frame, av.VideoFrame):
                frame_np = frame.to_ndarray(format="rgb24")
            else:
                frame_np = frame
                
            # Store the frame as a JPEG-encoded bytes object for efficient serving
            _, jpeg_frame = cv2.imencode('.jpg', cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR), 
                                        [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            
            self.current_frame = jpeg_frame.tobytes()
            self.last_update_time = time.time()
    
    def get_current_frame(self) -> Optional[bytes]:
        """Get the current frame from the buffer"""
        with self.frame_lock:
            return self.current_frame
