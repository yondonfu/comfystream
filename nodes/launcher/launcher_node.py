"""ComfyStream launcher node implementation"""
import os
import sys
import webbrowser
from server import PromptServer
from aiohttp import web
import pathlib
import subprocess
import signal
import atexit
import shutil

routes = PromptServer.instance.routes

# Get the path to the UI directory
UI_DIR = pathlib.Path(__file__).parent.parent.parent / "ui"
dev_server_process = None

def start_dev_server():
    """Start the Next.js dev server"""
    global dev_server_process
    if dev_server_process is None:
        try:
            print("[ComfyStream] Starting dev server...")
            npm_cmd = shutil.which("npm")
            if npm_cmd is None:
                raise RuntimeError("npm not found in PATH")
            # Start the dev server on port 3000
            dev_server_process = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=UI_DIR,
                env={**os.environ, "PORT": "3000"},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("[ComfyStream] Dev server started")
        except Exception as e:
            print(f"[ComfyStream] Error starting dev server: {str(e)}")
            raise

def cleanup_dev_server():
    """Cleanup the dev server process"""
    global dev_server_process
    if dev_server_process:
        print("[ComfyStream] Shutting down dev server...")
        if sys.platform == "win32":
            # On Windows, we need to use taskkill to kill the process tree
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(dev_server_process.pid)])
        else:
            # On Unix-like systems, we can use process group
            os.killpg(os.getpgid(dev_server_process.pid), signal.SIGTERM)
        dev_server_process = None

# Register cleanup on exit
atexit.register(cleanup_dev_server)

@routes.post('/launch_comfystream')
async def launch_comfystream(request):
    try:
        # Start the dev server if not running
        start_dev_server()
        # Open browser to the dev server
        webbrowser.open("http://localhost:3000")
        return web.json_response({"success": True})
    except Exception as e:
        print(f"Error in launch_comfystream: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)

class ComfyStreamLauncher:
    """Node that launches ComfyStream with the current workflow"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {}}  # No inputs needed
    
    RETURN_TYPES = ()
    FUNCTION = "do_nothing"
    CATEGORY = "comfystream"
    OUTPUT_NODE = True

    def do_nothing(self):
        """Do nothing"""
        return {}

    @classmethod
    def IS_CHANGED(cls, port):
        return float("NaN") # Always update
