import copy
import random

from typing import Dict, Any
# from comfy.api.components.schema.prompt import Prompt, PromptDictInput

import logging

def create_load_tensor_node():
    return {
        "inputs": {
            "tensor_data": ""  # Empty tensor data that will be filled at runtime
        },
        "class_type": "LoadTensorAPI",
        "_meta": {"title": "Load Tensor (API)"},
    }

def create_save_tensor_node(inputs: Dict[Any, Any]):
    """Create a SaveTensorAPI node with proper input formatting"""
    # Make sure images input is properly formatted [node_id, output_index]
    images_input = inputs.get("images")
    
    # If images input is not properly formatted as [node_id, output_index]
    if not isinstance(images_input, list) or len(images_input) != 2:
        print(f"Warning: Invalid images input format: {images_input}, using default")
        images_input = ["", 0]  # Default empty value
    
    return {
        "inputs": {
            "images": images_input,  # Should be [node_id, output_index]
            "format": "png",  # Better default than JPG for quality
            "quality": 95
        },
        "class_type": "SaveTensorAPI", 
        "_meta": {"title": "Save Tensor (API)"},
    }

def convert_prompt(prompt):

    logging.info("Converting prompt: %s", prompt)

    # Set random seeds for any seed nodes
    for key, node in prompt.items():
        if not isinstance(node, dict) or "inputs" not in node:
            continue
            
        # Check if this node has a seed input directly
        if "seed" in node.get("inputs", {}):
            # Generate a random seed (same range as JavaScript's Math.random() * 18446744073709552000)
            random_seed = random.randint(0, 18446744073709551615)
            node["inputs"]["seed"] = random_seed
            print(f"Set random seed {random_seed} for node {key}")


    # Replace LoadImage with LoadImageBase64
    for key, node in prompt.items():
        if node.get("class_type") == "LoadImage":
            node["class_type"] = "LoadImageBase64"

    # Replace SaveImage/PreviewImage with SendImageWebsocket
    for key, node in prompt.items():
        if node.get("class_type") in ["SaveImage", "PreviewImage"]:
            node["class_type"] = "SendImageWebsocket"
            # Ensure format is set
            if "format" not in node["inputs"]:
                node["inputs"]["format"] = "PNG"  # Set default format
            
    return prompt

'''
def convert_prompt(prompt: PromptDictInput) -> Prompt:
    # Validate the schema
    Prompt.validate(prompt)

    prompt = copy.deepcopy(prompt)

    num_primary_inputs = 0
    num_inputs = 0
    num_outputs = 0

    keys = {
        "PrimaryInputLoadImage": [],
        "LoadImage": [],
        "PreviewImage": [],
        "SaveImage": [],
    }
    
    for key, node in prompt.items():
        class_type = node.get("class_type")

        # Collect keys for nodes that might need to be replaced
        if class_type in keys:
            keys[class_type].append(key)

        # Count inputs and outputs
        if class_type == "PrimaryInputLoadImage":
            num_primary_inputs += 1
        elif class_type in ["LoadImage", "LoadTensor", "LoadAudioTensor"]:
            num_inputs += 1
        elif class_type in ["PreviewImage", "SaveImage", "SaveTensor", "SaveAudioTensor"]:
            num_outputs += 1

    # Only handle single primary input
    if num_primary_inputs > 1:
        raise Exception("too many primary inputs in prompt")

    # If there are no primary inputs, only handle single input
    if num_primary_inputs == 0 and num_inputs > 1:
        raise Exception("too many inputs in prompt")

    # Only handle single output for now
    if num_outputs > 1:
        raise Exception("too many outputs in prompt")

    if num_primary_inputs + num_inputs == 0:
        raise Exception("missing input")

    if num_outputs == 0:
        raise Exception("missing output")

    # Replace nodes
    for key in keys["PrimaryInputLoadImage"]:
        prompt[key] = create_load_tensor_node()

    if num_primary_inputs == 0 and len(keys["LoadImage"]) == 1:
        prompt[keys["LoadImage"][0]] = create_load_tensor_node()

    for key in keys["PreviewImage"] + keys["SaveImage"]:
        node = prompt[key]
        prompt[key] = create_save_tensor_node(node["inputs"])

    # Validate the processed prompt input
    prompt = Prompt.validate(prompt)

    return prompt
'''