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

class ComfyStreamServer:
    """Manages the ComfyStream server process"""
    
    def __init__(self):
        self.process = None
        self.port = None
        self.is_running = False
        atexit.register(self.cleanup)
        logging.info("ComfyStream server manager initialized")
        
    def find_available_port(self, start_port=8889):
        """Find an available port starting from start_port"""
        port = start_port
        while port < 65535:
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
        
        url = f"http://127.0.0.1:{self.port}"
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
            
            # Get the path to the ComfyStream server directory
            server_dir = Path(__file__).parent.parent / "server"
            logging.info(f"Server directory: {server_dir}")
            
            # Get ComfyUI workspace path
            comfyui_workspace = Path(__file__).parent.parent.parent.parent
            logging.info(f"ComfyUI workspace: {comfyui_workspace}")
            
            # Use the system Python (which should have ComfyStream installed)
            cmd = [sys.executable, "-u", str(server_dir / "app.py"),
                  "--port", str(self.port),
                  "--workspace", str(comfyui_workspace)]
            
            logging.info(f"Starting server with command: {' '.join(cmd)}")
            
            # Start process with output going to stdout/stderr
            self.process = subprocess.Popen(
                cmd,
                stdout=sys.stdout,
                stderr=sys.stderr,
                cwd=str(server_dir),
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            
            # Wait for server to start responding
            logging.info("Waiting for server to start...")
            for _ in range(30):  # Try for 30 seconds
                if self.check_server_health():
                    logging.info("Server is running!")
                    break
                await asyncio.sleep(1)
            else:
                raise RuntimeError("Server failed to start after 30 seconds")
            
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

    async def restart(self):
        """Restart the ComfyStream server"""
        logging.info("Restarting ComfyStream server...")
        current_port = self.port
        await self.stop()
        return await self.start(current_port)

    def get_status(self):
        """Get current server status"""
        status = {
            "running": self.is_running,
            "port": self.port,
            "pid": self.process.pid if self.process else None
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