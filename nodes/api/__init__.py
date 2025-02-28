"""ComfyStream API implementation"""
import os
import webbrowser
from server import PromptServer
from aiohttp import web
import pathlib
import logging
import aiohttp
from ..server_manager import LocalComfyStreamServer
from .. import settings_storage

routes = None
server_manager = None

# Only set up routes if we're in the main ComfyUI instance
if hasattr(PromptServer.instance, 'routes') and hasattr(PromptServer.instance.routes, 'static'):
    routes = PromptServer.instance.routes
    
    # Get the path to the static build directory
    STATIC_DIR = pathlib.Path(__file__).parent.parent.parent / "nodes" / "web" / "static"    
    
    # Dynamically determine the extension name from the directory structure
    try:
        # Get the parent directory of the current file
        # Then navigate up to get the extension root directory
        EXTENSION_ROOT = pathlib.Path(__file__).parent.parent.parent
        # Get the extension name (the directory name)
        EXTENSION_NAME = EXTENSION_ROOT.name
        logging.info(f"Detected extension name: {EXTENSION_NAME}")
    except Exception as e:
        logging.warning(f"Failed to get extension name dynamically: {e}")
        # Fallback to the hardcoded name
        EXTENSION_NAME = "comfystream"
    
    # Add static route for Next.js build files using the dynamic extension name
    STATIC_ROUTE = f"/extensions/{EXTENSION_NAME}/static"
    logging.info(f"Setting up static route: {STATIC_ROUTE} -> {STATIC_DIR}")
    routes.static(STATIC_ROUTE, str(STATIC_DIR), append_version=False, follow_symlinks=True)
    
    # Create server manager instance
    server_manager = LocalComfyStreamServer()
    
    @routes.get('/comfystream/extension_info')
    async def get_extension_info(request):
        """Return extension information including name and paths"""
        try:
            return web.json_response({
                "success": True,
                "extension_name": EXTENSION_NAME,
                "static_route": STATIC_ROUTE,
                "ui_url": f"{STATIC_ROUTE}/index.html"
            })
        except Exception as e:
            logging.error(f"Error getting extension info: {str(e)}")
            return web.json_response({"success": False, "error": str(e)}, status=500)
    
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
            settings = data.get("settings", {})
            
            # Extract host and port from settings if provided
            host = settings.get("host") if settings else None
            port = settings.get("port") if settings else None
            
            if action == "status":
                # Simply return the current server status
                return web.json_response({
                    "success": True,
                    "status": server_manager.get_status()
                })
            elif action == "start":
                success = await server_manager.start(port=port, host=host)
                return web.json_response({
                    "success": success,
                    "status": server_manager.get_status()
                })
            elif action == "stop":
                try:
                    success = await server_manager.stop()
                    return web.json_response({
                        "success": success,
                        "status": server_manager.get_status()
                    })
                except Exception as e:
                    logging.error(f"Error stopping server: {str(e)}")
                    # Force cleanup even if the normal stop fails
                    server_manager.cleanup()
                    return web.json_response({
                        "success": True,
                        "status": {"running": False, "port": None, "host": None, "pid": None, "type": "local"},
                        "message": "Forced server shutdown due to error"
                    })
            elif action == "restart":
                success = await server_manager.restart(port=port, host=host)
                return web.json_response({
                    "success": success,
                    "status": server_manager.get_status()
                })
            else:
                return web.json_response({"error": "Invalid action"}, status=400)
        except Exception as e:
            logging.error(f"Error controlling server: {str(e)}")
            # If we're trying to stop the server and get an error, force cleanup
            if data and data.get("action") == "stop":
                try:
                    server_manager.cleanup()
                    return web.json_response({
                        "success": True,
                        "status": {"running": False, "port": None, "host": None, "pid": None, "type": "local"},
                        "message": "Forced server shutdown due to error"
                    })
                except Exception as cleanup_error:
                    logging.error(f"Error during forced cleanup: {str(cleanup_error)}")
            
            return web.json_response({"error": str(e)}, status=500)

    @routes.get('/comfystream/settings')
    async def get_settings(request):
        """Get ComfyStream settings"""
        try:
            settings = settings_storage.load_settings()
            return web.json_response(settings)
        except Exception as e:
            logging.error(f"Error getting settings: {str(e)}")
            return web.json_response({"error": str(e)}, status=500)
    
    @routes.post('/comfystream/settings')
    async def update_settings(request):
        """Update ComfyStream settings"""
        try:
            data = await request.json()
            success = settings_storage.update_settings(data)
            return web.json_response({
                "success": success,
                "settings": settings_storage.load_settings()
            })
        except Exception as e:
            logging.error(f"Error updating settings: {str(e)}")
            return web.json_response({"error": str(e)}, status=500)
    
    @routes.post('/comfystream/settings/configuration')
    async def manage_configuration(request):
        """Add, remove, or select a configuration"""
        try:
            data = await request.json()
            action = data.get("action")
            
            if action == "add":
                name = data.get("name")
                host = data.get("host")
                port = data.get("port")
                if not name or not host or not port:
                    return web.json_response({"error": "Missing required parameters"}, status=400)
                
                success = settings_storage.add_configuration(name, host, port)
                return web.json_response({
                    "success": success,
                    "settings": settings_storage.load_settings()
                })
            
            elif action == "remove":
                index = data.get("index")
                if index is None:
                    return web.json_response({"error": "Missing index parameter"}, status=400)
                
                success = settings_storage.remove_configuration(index)
                return web.json_response({
                    "success": success,
                    "settings": settings_storage.load_settings()
                })
            
            elif action == "select":
                index = data.get("index")
                if index is None:
                    return web.json_response({"error": "Missing index parameter"}, status=400)
                
                success = settings_storage.select_configuration(index)
                return web.json_response({
                    "success": success,
                    "settings": settings_storage.load_settings()
                })
            
            else:
                return web.json_response({"error": "Invalid action"}, status=400)
        except Exception as e:
            logging.error(f"Error managing configuration: {str(e)}")
            return web.json_response({"error": str(e)}, status=500)

