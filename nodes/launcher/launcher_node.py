"""ComfyStream launcher node implementation"""
import os
import webbrowser
from server import PromptServer
from aiohttp import web
import pathlib
import logging
import aiohttp
from ..server_manager import ComfyStreamServer

routes = PromptServer.instance.routes

# Get the path to the static build directory
STATIC_DIR = pathlib.Path(__file__).parent.parent.parent / "nodes" / "web" / "static"

# Add static route for Next.js build files
routes.static('/extensions/comfystream_inside/static', str(STATIC_DIR))

# Create server manager instance
server_manager = ComfyStreamServer()

@routes.post('/api/offer')
async def proxy_offer(request):
    """Proxy offer requests to the ComfyStream server"""
    try:
        data = await request.json()
        target_url = data.get("endpoint")
        if not target_url:
            return web.json_response({"error": "No endpoint provided"}, status=400)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{target_url}/offer",
                json={"prompt": data.get("prompt"), "offer": data.get("offer")},
                headers={"Content-Type": "application/json"}
            ) as response:
                if not response.ok:
                    return web.json_response(
                        {"error": f"Server error: {response.status}"}, 
                        status=response.status
                    )
                return web.json_response(await response.json())
    except Exception as e:
        logging.error(f"Error proxying offer: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post('/comfystream/control')
async def control_server(request):
    """Handle server control requests"""
    try:
        data = await request.json()
        action = data.get("action")
        
        if action == "start":
            success = await server_manager.start()
        elif action == "stop":
            success = await server_manager.stop()
        elif action == "restart":
            success = await server_manager.restart()
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
