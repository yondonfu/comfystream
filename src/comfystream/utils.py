import copy
import json
import os
import logging
import importlib
from typing import Dict, Any, List, Tuple, Optional, Union
from pytrickle.api import StreamParamsUpdateRequest
from comfy.api.components.schema.prompt import Prompt, PromptDictInput
from .modalities import (
    get_node_counts_by_type,
    get_convertible_node_keys,
)

def create_load_tensor_node():
    return {
        "inputs": {},
        "class_type": "LoadTensor",
        "_meta": {"title": "LoadTensor"},
    }

def create_save_tensor_node(inputs: Dict[Any, Any]):
    return {
        "inputs": inputs,
        "class_type": "SaveTensor",
        "_meta": {"title": "SaveTensor"},
    }

def _validate_prompt_constraints(counts: Dict[str, int]) -> None:
    """Validate that the prompt meets the required constraints."""
    if counts["primary_inputs"] > 1:
        raise Exception("too many primary inputs in prompt")

    if counts["primary_inputs"] == 0 and counts["inputs"] > 2:
        raise Exception("too many inputs in prompt")

    if counts["outputs"] > 3:
        raise Exception("too many outputs in prompt")

    if counts["primary_inputs"] + counts["inputs"] == 0:
        raise Exception("missing input")

    if counts["outputs"] == 0:
        raise Exception("missing output")

def convert_prompt(prompt: PromptDictInput, return_dict: bool = False) -> Prompt:
    """Convert a prompt by replacing specific node types with tensor equivalents."""
    try:
        # Note: lazy import is necessary to prevent KeyError during validation
        importlib.import_module("comfy.api.components.schema.prompt_node")
    except Exception:
        pass
    
    """Convert and validate a ComfyUI workflow prompt."""
    Prompt.validate(prompt)
    prompt = copy.deepcopy(prompt)

    # Count nodes and validate constraints
    counts = get_node_counts_by_type(prompt)
    _validate_prompt_constraints(counts)
    
    # Collect nodes that need conversion
    convertible_keys = get_convertible_node_keys(prompt)

    # Replace nodes based on their conversion type
    for key in convertible_keys["PrimaryInputLoadImage"]:
        prompt[key] = create_load_tensor_node()

    # Conditional replacement: only if no primary input and exactly one LoadImage
    if counts["primary_inputs"] == 0 and len(convertible_keys["LoadImage"]) == 1:
        prompt[convertible_keys["LoadImage"][0]] = create_load_tensor_node()

    # Replace output nodes
    for key in convertible_keys["PreviewImage"] + convertible_keys["SaveImage"]:
        node = prompt[key]
        prompt[key] = create_save_tensor_node(node["inputs"])

    # Return dict if requested (for downstream components that expect plain dicts)
    if return_dict:
        return prompt  # Already a plain dict at this point
    
    # Validate the processed prompt and return Pydantic object
    return Prompt.validate(prompt)

class ComfyStreamParamsUpdateRequest(StreamParamsUpdateRequest):
    """ComfyStream parameter validation."""
    
    def __init__(self, **data):
        # Handle prompts parameter
        if "prompts" in data:
            prompts = data["prompts"]
            
            # Parse JSON string if needed
            if isinstance(prompts, str) and prompts.strip():
                try:
                    prompts = json.loads(prompts)
                except json.JSONDecodeError:
                    data.pop("prompts")
            
            # Handle list - use first valid dict
            elif isinstance(prompts, list):
                prompts = next((p for p in prompts if isinstance(p, dict)), None)
                if not prompts:
                    data.pop("prompts")
            
            # Validate prompts
            if "prompts" in data and isinstance(prompts, dict):
                try:
                    data["prompts"] = convert_prompt(prompts, return_dict=True)
                except Exception:
                    data.pop("prompts")
        
        # Call parent constructor
        super().__init__(**data)
    
    @classmethod
    def model_validate(cls, obj):
        return cls(**obj)
    
    def model_dump(self):
        return super().model_dump()

def get_default_workflow() -> dict:
    """Return the default workflow as a dictionary for warmup.
    
    Returns:
        dict: Default workflow dictionary
    """
    return {
        "1": {
            "inputs": {
                "images": [
                    "2",
                    0
                ]
            },
            "class_type": "SaveTensor",
            "_meta": {
                "title": "SaveTensor"
            }
        },
        "2": {
            "inputs": {},
            "class_type": "LoadTensor",
            "_meta": {
                "title": "LoadTensor"
            }
        }
    }

