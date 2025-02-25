"""ComfyStream launcher node implementation"""
import os
import webbrowser
from server import PromptServer
from aiohttp import web
import pathlib
import logging
import aiohttp
from ..server_manager import LocalComfyStreamServer

routes = None
server_manager = None

# Only set up routes if we're in the main ComfyUI instance
if hasattr(PromptServer.instance, 'routes') and hasattr(PromptServer.instance.routes, 'static'):
    routes = PromptServer.instance.routes
    
    # Get the path to the static build directory
    STATIC_DIR = pathlib.Path(__file__).parent.parent.parent / "nodes" / "web" / "static"    
    
    # Dynamically determine the extension name from the directory structure
    try:
        # Get the parent directory of the current file (launcher_node.py)
        # Then navigate up to get the extension root directory
        EXTENSION_ROOT = pathlib.Path(__file__).parent.parent.parent
        # Get the extension name (the directory name)
        EXTENSION_NAME = EXTENSION_ROOT.name
        logging.info(f"Detected extension name: {EXTENSION_NAME}")
    except Exception as e:
        logging.warning(f"Failed to get extension name dynamically: {e}")
        # Fallback to the hardcoded name
        EXTENSION_NAME = "ComfyStream"
    
    # Add static route for Next.js build files using the dynamic extension name
    STATIC_ROUTE = f"/extensions/{EXTENSION_NAME}/static"
    logging.info(f"Setting up static route: {STATIC_ROUTE} -> {STATIC_DIR}")
    routes.static(STATIC_ROUTE, str(STATIC_DIR), append_version=False, follow_symlinks=True)
    
    # Create server manager instance
    server_manager = LocalComfyStreamServer()
    
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
                    json={"prompts": data.get("prompts"), "offer": data.get("offer")},
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
            # Open browser to the static UI using the dynamic extension name
            webbrowser.open(f"http://localhost:8188{STATIC_ROUTE}/index.html")
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
