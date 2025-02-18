"""ComfyStream launcher node implementation"""
import os
import webbrowser
from server import PromptServer
from aiohttp import web
import pathlib
import logging
from ..server_manager import ComfyStreamServer

routes = PromptServer.instance.routes

# Get the path to the static build directory
STATIC_DIR = pathlib.Path(__file__).parent.parent.parent / "nodes" / "web" / "static"

# Add static route for Next.js build files
routes.static('/extensions/comfystream_inside/static', str(STATIC_DIR))

# Create server manager instance
server_manager = ComfyStreamServer()

@routes.post('/comfystream/control')
async def control_server(request):
    """Handle server control requests"""
    try:
        data = await request.json()
        action = data.get("action")
        
        if action == "start":
            success = await server_manager.start()
            if success:
                # Open browser to ComfyStream UI on its own port
                webbrowser.open(f"http://localhost:{server_manager.port}")
        elif action == "stop":
            success = await server_manager.stop()
        elif action == "restart":
            success = await server_manager.restart()
            if success:
                webbrowser.open(f"http://localhost:{server_manager.port}")
        else:
            return web.json_response({"error": "Invalid action"}, status=400)

        return web.json_response({
            "success": success,
            "status": server_manager.get_status()
        })
    except Exception as e:
        logging.error(f"Error controlling server: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post('/launch_comfystream')
async def launch_comfystream(request):
    """Open the ComfyStream UI in a new browser tab"""
    try:
        # Open browser to the static UI
        webbrowser.open("http://localhost:8188/extensions/comfystream_inside/static/index.html")
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error launching ComfyStream UI: {str(e)}")
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
