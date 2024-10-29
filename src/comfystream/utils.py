import copy

from comfy.api.components.schema.prompt import Prompt, PromptDictInput


def convert_prompt(prompt: PromptDictInput) -> Prompt:
    # Validate the schema
    Prompt.validate(prompt)

    prompt = copy.deepcopy(prompt)

    num_inputs = 0
    num_outputs = 0

    for key, node in prompt.items():
        if node.get("class_type") == "LoadImage":
            num_inputs += 1

            prompt[key] = {
                "inputs": {},
                "class_type": "LoadTensor",
                "_meta": {"title": "LoadTensor"},
            }
        elif node.get("class_type") in ["PreviewImage", "SaveImage"]:
            num_outputs += 1

            prompt[key] = {
                "inputs": node["inputs"],
                "class_type": "SaveTensor",
                "_meta": {"title": "SaveTensor"},
            }
        elif node.get("class_type") == "LoadTensor":
            num_inputs += 1
        elif node.get("class_type") == "SaveTensor":
            num_outputs += 1

    # Only handle single input for now
    if num_inputs > 1:
        raise Exception("too many inputs in prompt")

    # Only handle single output for now
    if num_outputs > 1:
        raise Exception("too many outputs in prompt")

    if num_inputs == 0:
        raise Exception("missing input")

    if num_outputs == 0:
        raise Exception("missing output")

    # Validate the processed prompt input
    prompt = Prompt.validate(prompt)

    return prompt
