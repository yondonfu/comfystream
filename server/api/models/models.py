import asyncio
from pathlib import Path
import os
import logging
from aiohttp import ClientSession

logger = logging.getLogger(__name__)

async def list_models(workspace_dir):
    models_path = Path(os.path.join(workspace_dir, "models"))
    models_path.mkdir(parents=True, exist_ok=True)
    os.chdir(models_path)

    model_types = ["checkpoints", "controlnet", "unet", "vae", "onnx", "tensorrt"]
    
    models = {}
    try:
        for model_type in models_path.iterdir():
            model_name = ""
            model_subfolder = ""
            model_type_name = model_type.name
            if model_type.is_dir():
                models[model_type_name] = []
                for model in model_type.iterdir():
                    if model.is_dir():
                        #models in subfolders (e.g. checkpoints/sd1.5/model.safetensors)
                        for submodel in model.iterdir():
                            if submodel.is_file():
                                model_name = submodel.name
                                model_subfolder = model.name
                    else:
                        #models not in subfolders (e.g. checkpoints/model.safetensors)
                        logger.info(f"model: {model.name}")
                        model_name = model.name
                        model_subfolder = ""

                    #add model to list
                    model_info = await create_model_info(model_name, model_subfolder, model_type_name)
                    models[model_type_name].append(model_info)
            else:
                if not model_type.name in model_types:
                    models["none"] = []

                model_name = model_type_name
                model_subfolder = ""

                #add model to list
                model_info = await create_model_info(model_name, model_subfolder, model_type_name)
                models[model_type_name].append(model_info)
    except Exception as e:
        logger.error(f"error listing models: {e}")
        raise Exception(f"error listing models: {e}")
    return models

async def create_model_info(model, model_subfolder, model_type):
    model_path = f"{model_subfolder}/{model}" if model_subfolder else model
    logger.info(f"adding info for model: {model_type}/{model_path}")
    model_info = {
        "name": model,
        "path": model_path,
        "type": model_type,
        "downloading": os.path.exists(f"{model_path}.downloading")
    }
    return model_info

async def add_model(model, workspace_dir):
    if not 'url' in model:
        raise Exception("model url is required")
    if not 'type' in model:
        raise Exception("model type is required (e.g. checkpoints, controlnet, unet, vae, onnx, tensorrt)")
    
    try:
        model_name = model['url'].split("/")[-1]
        model_path = Path(os.path.join(workspace_dir, "models", model['type'], model_name))
        #if specified, use the model path from the model dict (e.g. sd1.5/model.safetensors will put model.safetensors in models/checkpoints/sd1.5)
        if 'path' in model:
            model_path = Path(os.path.join(workspace_dir, "models", model['type'], model['path']))
            logger.info(f"model path: {model_path}")
        
        # check path is in workspace_dir, raises value error if not
        model_path.resolve().relative_to(Path(os.path.join(workspace_dir, "models")))
        os.makedirs(model_path.parent, exist_ok=True)
        # start downloading the model in background without blocking
        asyncio.create_task(download_model(model['url'], model_path))
    except Exception as e:
        os.remove(model_path)+".downloading"
        raise Exception(f"error downloading model: {e}")

async def delete_model(model, workspace_dir):
    if not 'type' in model:
        raise Exception("model type is required (e.g. checkpoints, controlnet, unet, vae, onnx, tensorrt)")
    if not 'path' in model:
        raise Exception("model path is required")
    try:
        model_path = Path(os.path.join(workspace_dir, "models", model['type'], model['path']))
        #check path is in workspace_dir, raises value error if not
        model_path.resolve().relative_to(Path(os.path.join(workspace_dir, "models")))
        
        os.remove(model_path)
    except Exception as e:
        raise Exception(f"error deleting model: {e}")
    
async def download_model(url: str, save_path: Path):
    try:
        temp_file = save_path.with_suffix(save_path.suffix + ".downloading")
        print("downloading")
        async with ClientSession() as session:
            logger.info(f"downloading model from {url} to {save_path}")
            # Create empty file to track download in process
            model_name = os.path.basename(save_path)
            
            open(temp_file, "w").close()
        
            async with session.get(url) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('Content-Length', 0))
                    total_downloaded = 0
                    last_logged_percentage = -1  # Ensures first log at 1%
                    with open(save_path, "wb") as f:
                        while chunk := await response.content.read(4096):  # Read in chunks of 1KB
                            f.write(chunk)
                            total_downloaded += len(chunk)
                            # Calculate percentage and log only if it has increased by 1%
                            percentage = (total_downloaded / total_size) * 100
                            if int(percentage) > last_logged_percentage:
                                last_logged_percentage = int(percentage)
                                logger.info(f"Downloaded {total_downloaded} of {total_size} bytes ({percentage:.2f}%) of {model_name}")
                            
                    #remove download in process file
                    os.remove(temp_file)
                    logger.info(f"Model downloaded and saved to {save_path}")
                else:
                    raise print(f"Failed to download model. HTTP Status: {response.status}")
    except Exception as e:
        #remove download in process file
        logger.error(f"error downloading model: {str(e)}")
        os.remove(temp_file)