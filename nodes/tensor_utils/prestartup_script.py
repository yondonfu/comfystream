import torch

print("Loading pre-startup script for controlnet torch.compile() compatibility...")

def patch_controlnet_for_stream():
    """Patch ControlNet for better compatibility with torch.compile()"""
    try:
        from comfy.controlnet import ControlBase
        original_control_merge = ControlBase.control_merge
       
        def wrapped_control_merge(self, control, control_prev, output_dtype):
            # Mark CUDA graph step at start
            if torch.cuda.is_available() and hasattr(torch.compiler, 'cudagraph_mark_step_begin'):
                torch.compiler.cudagraph_mark_step_begin()
                torch.cuda.synchronize()
               
            # Deep clone control outputs to prevent CUDA graph overwrites
            control = {
                k: [t.clone() if t is not None else None for t in v]
                for k, v in control.items()
            }
           
            # Deep clone previous control if it exists
            if control_prev is not None:
                control_prev = {
                    k: [t.clone() if t is not None else None for t in v]
                    for k, v in control_prev.items()
                }
               
            # Get result from original merge function
            result = original_control_merge(self, control, control_prev, output_dtype)
           
            # Clone all output tensors
            result = {
                k: [t.clone() if t is not None else None for t in v]
                for k, v in result.items()
            }
           
            # Mark CUDA graph step at end
            if torch.cuda.is_available() and hasattr(torch.compiler, 'cudagraph_mark_step_begin'):
                torch.compiler.cudagraph_mark_step_begin()
                torch.cuda.synchronize()
               
            return result
           
        # Apply the patch
        ControlBase.control_merge = wrapped_control_merge
        print("Successfully patched ControlNet for torch.compile() compatibility")
    except Exception as e:
        print(f"Warning: Failed to patch ControlNet: {str(e)}")

# Apply patch when module is imported
patch_controlnet_for_stream() 