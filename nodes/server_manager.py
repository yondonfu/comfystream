"""ComfyStream server management module"""
import os
import sys
import subprocess
import socket
import signal
import atexit
import logging
import urllib.request
import urllib.error
from pathlib import Path
import time
import asyncio
from abc import ABC, abstractmethod

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='[ComfyStream] %(message)s',
    stream=sys.stdout
)

# Set up Windows specific event loop policy
if sys.platform == 'win32':
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        

class ComfyStreamServerBase(ABC):
    """Abstract base class for ComfyStream server management"""
    
    def __init__(self, host="127.0.0.1", port=None):
        self.host = host
        self.port = port
        self.is_running = False
        logging.info(f"Initializing {self.__class__.__name__}")
    
    @abstractmethod
    async def start(self, port=None) -> bool:
        """Start the ComfyStream server
        
        Args:
            port: Optional port to use. If None, implementation should choose a port.
            
        Returns:
            bool: True if server started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the ComfyStream server
        
        Returns:
            bool: True if server stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_status(self) -> dict:
        """Get current server status
        
        Returns:
            dict: Server status information
        """
        pass
    
    @abstractmethod
    def check_server_health(self) -> bool:
        """Check if server is responding to health checks
        
        Returns:
            bool: True if server is healthy, False otherwise
        """
        pass
    
    async def restart(self) -> bool:
        """Restart the ComfyStream server
        
        Returns:
            bool: True if server restarted successfully, False otherwise
        """
        logging.info("Restarting ComfyStream server...")
        current_port = self.port
        await self.stop()
        return await self.start(current_port)

class LocalComfyStreamServer(ComfyStreamServerBase):
    """Local ComfyStream server implementation"""
    
    def __init__(self, host="127.0.0.1", start_port=8889, max_port=65535, 
                 health_check_timeout=30, health_check_interval=1):
        super().__init__(host=host)
        self.process = None
        self.start_port = start_port
        self.max_port = max_port
        self.health_check_timeout = health_check_timeout
        self.health_check_interval = health_check_interval
        atexit.register(self.cleanup)
        
    def find_available_port(self):
        """Find an available port starting from start_port"""
        port = self.start_port
        while port < self.max_port:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    logging.info(f"Found available port: {port}")
                    return port
            except OSError:
                port += 1
        raise RuntimeError("No available ports found")

    def check_server_health(self):
        """Check if server is responding to health checks"""
        if not self.port:
            return False
        
        url = f"http://{self.host}:{self.port}"
        try:
            response = urllib.request.urlopen(url)
            return response.code == 200
        except urllib.error.URLError:
            return False

    async def start(self, port=None):
        """Start the ComfyStream server"""
        if self.is_running:
            logging.info("Server is already running")
            return False

        try:
            self.port = port or self.find_available_port()
            
            # Get the path to the ComfyStream server directory and script
            server_dir = Path(__file__).parent.parent / "server"
            server_script = server_dir / "app.py"
            logging.info(f"Server script: {server_script}")
            
            # Get ComfyUI workspace path (which is where we'll run from)
            comfyui_workspace = Path(__file__).parent.parent.parent.parent
            logging.info(f"ComfyUI workspace: {comfyui_workspace}")
            
            # Use the system Python (which should have ComfyStream installed)
            cmd = [sys.executable, "-u", str(server_script),
                  "--port", str(self.port),
                  "--host", str(self.host),
                  "--workspace", str(comfyui_workspace)]
            
            logging.info(f"Starting server with command: {' '.join(cmd)}")
            
            # Start process with output going to stdout/stderr
            self.process = subprocess.Popen(
                cmd,
                stdout=sys.stdout,
                stderr=sys.stderr,
                cwd=str(comfyui_workspace),  # Run from ComfyUI root
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            
            # Wait for server to start responding
            logging.info("Waiting for server to start...")
            for _ in range(self.health_check_timeout):
                if self.check_server_health():
                    logging.info("Server is running!")
                    break
                await asyncio.sleep(self.health_check_interval)
            else:
                raise RuntimeError(f"Server failed to start after {self.health_check_timeout} seconds")
            
            if self.process.poll() is not None:
                raise RuntimeError(f"Server failed to start (exit code: {self.process.poll()})")
            
            self.is_running = True
            logging.info(f"ComfyStream server started on port {self.port} (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            logging.error(f"Error starting ComfyStream server: {str(e)}")
            self.cleanup()
            return False

    async def stop(self):
        """Stop the ComfyStream server"""
        if not self.is_running:
            logging.info("Server is not running")
            return False
            
        try:
            self.cleanup()
            logging.info("ComfyStream server stopped")
            return True
        except Exception as e:
            logging.error(f"Error stopping ComfyStream server: {str(e)}")
            return False

    def get_status(self):
        """Get current server status"""
        status = {
            "running": self.is_running,
            "port": self.port,
            "pid": self.process.pid if self.process else None,
            "type": "local"
        }
        logging.info(f"Server status: {status}")
        return status

    def cleanup(self):
        """Cleanup server process on exit"""
        if self.process:
            try:
                logging.info(f"Cleaning up server process (PID: {self.process.pid})")
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)])
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception as e:
                logging.error(f"Error cleaning up server process: {str(e)}")
            self.process = None
            self.is_running = False 