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
            
    return prompt

'''
def convert_prompt(prompt):

    # Check if this is a ComfyUI web UI format prompt with 'nodes' and 'links'
    if isinstance(prompt, dict) and 'nodes' in prompt and 'links' in prompt:
        # Convert the web UI prompt format to the API format
        api_prompt = {}
        
        # Process each node
        for node in prompt['nodes']:
            node_id = str(node['id'])
            
            # Create a node entry in the API format
            api_prompt[node_id] = {
                'class_type': node.get('type', 'Unknown'),
                'inputs': {},
                '_meta': {
                    'title': node.get('type', 'Unknown')
                }
            }
            
            # Process inputs
            if 'inputs' in node:
                for input_data in node['inputs']:
                    input_name = input_data.get('name')
                    link_id = input_data.get('link')
                    
                    if input_name and link_id is not None:
                        # Find the source of this link
                        for link in prompt['links']:
                            if link[0] == link_id:  # link ID matches
                                # Get source node and output slot
                                source_node_id = str(link[1])
                                source_slot = link[3]
                                
                                # Add to inputs
                                api_prompt[node_id]['inputs'][input_name] = [
                                    source_node_id,
                                    source_slot
                                ]
                                break
                        # If no link found, set to empty value
                        if input_name not in api_prompt[node_id]['inputs']:
                            api_prompt[node_id]['inputs'][input_name] = None
            
            # Process widget values
            if 'widgets_values' in node:
                for i, widget_value in enumerate(node.get('widgets_values', [])):
                    # Try to determine widget name from properties or use index
                    widget_name = f"widget_{i}"
                    # Add to inputs
                    api_prompt[node_id]['inputs'][widget_name] = widget_value
        
        # Use this converted prompt instead
        prompt = api_prompt
    
    # Now process as normal API format prompt
    prompt = copy.deepcopy(prompt)
    
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

    num_primary_inputs = 0
    num_inputs = 0
    num_outputs = 0

    keys = {
        "PrimaryInputLoadImage": [],
        "LoadImage": [],
        "PreviewImage": [],
        "SaveImage": [],
        "LoadTensor": [],
        "SaveTensor": [],
        "LoadImageBase64": [],
        "LoadTensorAPI": [],
        "SaveTensorAPI": [],
    }
    
    for key, node in prompt.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        
        # Track primary input and output nodes
        if class_type in ["PrimaryInput", "PrimaryInputImage"]:
            num_primary_inputs += 1
            keys["PrimaryInputLoadImage"].append(key)
        elif class_type in ["LoadImage", "LoadTensor", "LoadAudioTensor", "LoadImageBase64", "LoadTensorAPI"]:
            num_inputs += 1
            if class_type == "LoadImage":
                keys["LoadImage"].append(key)
            elif class_type == "LoadTensor": 
                keys["LoadTensor"].append(key)
            elif class_type == "LoadImageBase64":
                keys["LoadImageBase64"].append(key)
            elif class_type == "LoadTensorAPI":
                keys["LoadTensorAPI"].append(key)
        elif class_type in ["PreviewImage", "SaveImage", "SaveTensor", "SaveAudioTensor", "SendImageWebSocket", "SaveTensorAPI"]:
            num_outputs += 1
            if class_type == "PreviewImage":
                keys["PreviewImage"].append(key)
            elif class_type == "SaveImage":
                keys["SaveImage"].append(key)
            elif class_type == "SaveTensor":
                keys["SaveTensor"].append(key)
            elif class_type == "SaveTensorAPI":
                keys["SaveTensorAPI"].append(key)

    print(f"Found {num_primary_inputs} primary inputs, {num_inputs} inputs, {num_outputs} outputs")

    # Set up connection for video feeds by replacing LoadImage with LoadImageBase64
    if num_inputs == 0 and num_primary_inputs == 0:
        # Add a LoadTensorAPI node
        new_key = "999990"
        prompt[new_key] = create_load_tensor_node()
        keys["LoadTensorAPI"].append(new_key)
        print("Added LoadTensorAPI node for tensor input")
    elif len(keys["LoadTensor"]) > 0 and len(keys["LoadTensorAPI"]) == 0:
        # Replace LoadTensor with LoadTensorAPI if found
        for key in keys["LoadTensor"]:
            prompt[key] = create_load_tensor_node()
            keys["LoadTensorAPI"].append(key)
        print("Replaced LoadTensor with LoadTensorAPI")

    # Set up connection for output if needed
    if num_outputs == 0:
        # Find nodes that produce images
        image_output_nodes = []
        for key, node in prompt.items():
            if isinstance(node, dict):
                class_type = node.get("class_type", "")
                # Look for nodes that typically output images
                if any(output_type in class_type.lower() for output_type in ["vae", "decode", "img", "image", "upscale", "sample"]):
                    image_output_nodes.append(key)
                # Also check if the node's RETURN_TYPES includes IMAGE
                elif "outputs" in node and isinstance(node["outputs"], dict):
                    for output_name, output_type in node["outputs"].items():
                        if "IMAGE" in output_type:
                            image_output_nodes.append(key)
                            break
        
        # If we found image output nodes, connect SaveTensorAPI to them
        if image_output_nodes:
            for i, node_key in enumerate(image_output_nodes):
                new_key = f"999991_{i}"
                prompt[new_key] = create_save_tensor_node({"images": [node_key, 0]})
                print(f"Added SaveTensorAPI node connected to {node_key}")
        else:
            # Try to find the last node in the chain as fallback
            last_node = None
            max_id = -1
            for key, node in prompt.items():
                if isinstance(node, dict):
                    try:
                        node_id = int(key)
                        if node_id > max_id:
                            max_id = node_id
                            last_node = key
                    except ValueError:
                        pass
            
            if last_node:
                # Add a SaveTensorAPI node
                new_key = "999991"
                prompt[new_key] = create_save_tensor_node({"images": [last_node, 0]})
                print(f"Added SaveTensorAPI node connected to {last_node}")
            else:
                print("Warning: Could not find a suitable node to connect SaveTensorAPI to")
    
    # Make sure all SaveTensorAPI nodes have proper configuration
    for key, node in prompt.items():
        if isinstance(node, dict) and node.get("class_type") == "SaveTensorAPI":
            # Ensure format is set to PNG for optimal compatibility
            if "inputs" in node:
                node["inputs"]["format"] = "png"
    
    # Return the modified prompt
    return prompt
'''