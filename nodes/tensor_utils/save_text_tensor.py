from comfystream import tensor_cache

class SaveTextTensor:
    CATEGORY = "text_utils"
    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "data": ("STRING",),  # Accept text string as input.
            },
            "optional": {
                "remove_linebreaks": ("BOOLEAN", {"default": True}),  # Remove whitespace and line breaks
            }
        }

    @classmethod
    def IS_CHANGED(s, **kwargs):
        return float("nan")

    def execute(self, data, remove_linebreaks=True):
        if remove_linebreaks:
            result_text = data.replace('\n', '').replace('\r', '')
        else:
            result_text = data
        tensor_cache.text_outputs.put_nowait(result_text)
        return (result_text,)
