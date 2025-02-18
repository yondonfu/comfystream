"""ComfyStream server management module"""
import os
import sys
import subprocess
import socket
import signal
import atexit
import logging
from pathlib import Path

class ComfyStreamServer:
    """Manages the ComfyStream server process"""
    
    def __init__(self):
        self.process = None
        self.port = None
        self.is_running = False
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
    def find_available_port(self, start_port=3000):
        """Find an available port starting from start_port"""
        port = start_port
        while port < 65535:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                port += 1
        raise RuntimeError("No available ports found")

    def cleanup(self):
        """Cleanup server process on exit"""
        if self.process:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)])
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception as e:
                logging.error(f"Error cleaning up server process: {str(e)}")
            self.process = None
            self.is_running = False

    async def start(self, port=None):
        """Start the ComfyStream server"""
        if self.is_running:
            return False

        try:
            self.port = port or self.find_available_port()
            
            # Get the path to the ComfyStream server directory
            # Go up to the package root where server/ is located
            server_dir = Path(__file__).parent.parent.parent / "server"
            
            # Ensure the directory exists
            if not server_dir.exists():
                raise RuntimeError(f"Server directory not found at {server_dir}")
                
            # Ensure server.py exists
            server_script = server_dir / "server.py"
            if not server_script.exists():
                raise RuntimeError(f"server.py not found at {server_script}")
            
            # Start the server process
            self.process = subprocess.Popen(
                [sys.executable, str(server_script), "--port", str(self.port)],
                cwd=str(server_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # TODO: Wait for server to be ready by checking output or port
            self.is_running = True
            logging.info(f"ComfyStream server started on port {self.port}")
            return True
            
        except Exception as e:
            logging.error(f"Error starting ComfyStream server: {str(e)}")
            self.cleanup()
            return False

    async def stop(self):
        """Stop the ComfyStream server"""
        if not self.is_running:
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
        current_port = self.port
        await self.stop()
        return await self.start(current_port)

    def get_status(self):
        """Get current server status"""
        return {
            "running": self.is_running,
            "port": self.port,
            "pid": self.process.pid if self.process else None
        } 