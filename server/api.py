from utils import install_node, list_nodes


#hiddenswitch comfyui openapi spec
#https://github.com/hiddenswitch/ComfyUI/blob/master/comfy/api/openapi.yaml

def add_routes(app):
    app.router.add_get("/tool/list_nodes", nodes)
    app.router.add_post("/tool/install_nodes", install_nodes)

async def nodes(request):
    return await list_nodes(request.app['workspace'])

async def install_nodes(request):
    params = await request.json()
    try:
        for node in params["nodes"]:
            install_node(node, request.app["workspace"])
        
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

async def model(request):
    pass

async def add_model(request):
    pass

async def delete_model(request):
    pass