from pathlib import Path
import os
import json
from git import Repo
import logging
import sys
from aiohttp import web

from api.nodes.nodes import list_nodes, install_node, delete_node
from api.models.models import list_models, add_model, delete_model
from api.settings.settings import set_twilio_account_info

def add_routes(app):
    app.router.add_get("/env/list_nodes", nodes)
    app.router.add_post("/env/install_nodes", install_nodes)
    app.router.add_post("/env/delete_nodes", delete_nodes)

    app.router.add_get("/env/list_models", models)
    app.router.add_post("/env/add_models", add_models)
    app.router.add_post("/env/delete_models", delete_models)

    app.router.add_post("/env/set_account_info", set_account_info)


async def nodes(request):
    '''
    List all custom nodes in the workspace

    # Example response:
    {
        "error": null,
        "nodes": 
            [
                {
                    "name": ComfyUI-Custom-Node,
                    "version": "0.0.1",
                    "url": "https://github.com/custom-node-maker/ComfyUI-Custom-Node",
                    "branch": "main",
                    "commit": "uasfg98",
                    "update_available": false,
                },
                {
                    ...
                },
                {
                    ...
                }
            ]
    }
    
    '''
    workspace_dir = request.app["workspace"]
    try:
        nodes = await list_nodes(workspace_dir)
        return web.json_response({"error": None, "nodes": nodes})
    except Exception as e:
        return web.json_response({"error": str(e), "nodes": nodes}, status=500)

async def install_nodes(request):
    '''
    Install ComfyUI custom node from git repository.

    Installs requirements.txt from repository if present

    # Parameters:
      url: url of the git repository
      branch: branch of the git repository
      depdenencies: comma separated list of dependencies to install with pip (optional)

    # Example request:
    [
        {
            "url": "https://github.com/custom-node-maker/ComfyUI-Custom-Node",
            "branch": "main" 
        },
        {
            "url": "https://github.com/custom-node-maker/ComfyUI-Custom-Node",
            "branch": "main",
            "dependencies": "requests, numpy"
        }
    ]
    '''
    workspace_dir = request.app["workspace"]
    try:
        nodes = await request.json()
        installed_nodes = []
        for node in nodes:
            await install_node(node, workspace_dir)
            installed_nodes.append(node['url'])
        return web.json_response({"success": True, "error": None, "installed_nodes": installed_nodes})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e), "installed_nodes": installed_nodes}, status=500)

async def delete_nodes(request):
    '''
    Delete ComfyUI custom node

    # Parameters:
      name: name of the repository (e.g. ComfyUI-Custom-Node for url "https://github.com/custom-node-maker/ComfyUI-Custom-Node")

    # Example request:
    [
        {
            "name": "ComfyUI-Custom-Node"
        },
        {
            ...
        }
    ]
    '''
    workspace_dir = request.app["workspace"]
    try:
        nodes = await request.json()
        deleted_nodes = []
        for node in nodes:
            await delete_node(node, workspace_dir)
            deleted_nodes.append(node['name'])
        return web.json_response({"success": True, "error": None, "deleted_nodes": deleted_nodes})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e), "deleted_nodes": deleted_nodes}, status=500)

async def models(request):
    '''
    List all custom models in the workspace

    # Example response:
    {
        "error": null,
        "models":
            {
                "checkpoints": [
                    {
                        "name": "dreamshaper-8.safetensors",
                        "path": "SD1.5/dreamshaper-8.safetensors",
                        "type": "checkpoint",
                        "downloading": false"
                    }
                ],
                "controlnet": [
                    {
                        "name": "controlnet.sd15.safetensors",
                        "path": "SD1.5/controlnet.sd15.safetensors",
                        "type": "controlnet",
                        "downloading": false"
                    }
                ],
                "unet": [
                    {
                        "name": "unet.sd15.safetensors",
                        "path": "SD1.5/unet.sd15.safetensors",
                        "type": "unet",
                        "downloading": false"
                    }
                ],
                "vae": [
                    {
                        "name": "vae.safetensors",
                        "path": "vae.safetensors",
                        "type": "vae",
                        "downloading": false"
                    }
                ],
                "tensorrt": [
                    {
                        "name": "model.trt",
                        "path": "model.trt",
                        "type": "tensorrt",
                        "downloading": false"
                    }
                ]
            }
    }
    
    '''
    workspace_dir = request.app["workspace"]
    try:
        models = await list_models(workspace_dir)
        return web.json_response({"error": None, "models": models})
    except Exception as e:
        return web.json_response({"error": str(e), "models": models}, status=500)

async def add_models(request):
    '''
    Download models from url

    # Parameters:
      url: url of the git repository
      type: type of model (e.g. checkpoints, controlnet, unet, vae, onnx, tensorrt)
      path: path of the model. supports up to 1 subfolder (e.g. SD1.5/newmodel.safetensors)

    # Example request:
    [
        {
            "url": "http://url.to/model.safetensors",
            "type": "checkpoints" 
        },
        {
            "url": "http://url.to/controlnet.super.safetensors",
            "type": "controlnet",
            "path": "SD1.5/controlnet.super.safetensors"
        }
    ]
    '''
    workspace_dir = request.app["workspace"]
    try:
        models = await request.json()
        added_models = []
        for model in models:
            await add_model(model, workspace_dir)
            added_models.append(model['url'])
        return web.json_response({"success": True, "error": None, "added_models": added_models})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e), "added_nodes": added_models}, status=500)

async def delete_models(request):
    '''
    Delete model

    # Parameters:
      type: type of model (e.g. checkpoints, controlnet, unet, vae, onnx, tensorrt)
      path: path of the model. supports up to 1 subfolder (e.g. SD1.5/newmodel.safetensors)

    # Example request:
    [
        {
            "type": "checkpoints",
            "path": "model.safetensors"            
        },
        {
            "type": "controlnet",
            "path": "SD1.5/controlnet.super.safetensors"
        }
    ]
    '''
    workspace_dir = request.app["workspace"]
    try:
        models = await request.json()
        deleted_models = []
        for model in models:
            await delete_model(model, workspace_dir)
            deleted_models.append(model['path'])
        return web.json_response({"success": True, "error": None, "deleted_models": deleted_models})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e), "deleted_models": deleted_models}, status=500)

async def set_account_info(request):
    '''
    Set account info for ice server providers

    # Parameters:
      type: account type (e.g. twilio)
      account_id: account id from provider
      auth_token: auth token from provider

    # Example request:
    [
        {
            "type": "twilio",
            "account_id": "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "auth_token": "your_auth_token"
        },
        {
            ...
        }
    ]
    
    '''
    try:
        accounts = await request.json()
        accounts_updated = []
        for account in accounts:
            if 'type' in account:
                if account['type'] == 'twilio':
                    await set_twilio_account_info(account)
                    accounts_updated.append(account['type'])
        return web.json_response({"success": True, "error": None, "accounts_updated": accounts_updated})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e), "accounts_updated": accounts_updated}, status=500)
