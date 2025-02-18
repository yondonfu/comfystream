"""ComfyStream launcher node implementation"""
import os
import webbrowser
from server import PromptServer
from aiohttp import web
import pathlib

routes = PromptServer.instance.routes

# Get the path to the static build directory
STATIC_DIR = pathlib.Path(__file__).parent.parent.parent / "nodes" / "web" / "static"

@routes.post('/launch_comfystream')
async def launch_comfystream(request):
    try:
        # Open browser to the static file
        webbrowser.open("http://localhost:8188/extensions/comfystream_inside/static/index.html")
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
