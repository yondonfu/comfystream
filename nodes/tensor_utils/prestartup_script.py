import torch

print("Loading pre-startup script for controlnet torch.compile() compatibility...")

def patch_controlnet_for_stream():
    """Patch ControlNet.get_control for better compatibility with torch.compile()"""
    try:
        from comfy.controlnet import ControlNet
        original_get_control = ControlNet.get_control
        
        def wrapped_get_control(self, x_noisy, t, cond, batched_number, transformer_options):
            # Mark CUDA graph step at start
            if torch.cuda.is_available() and hasattr(torch.compiler, 'cudagraph_mark_step_begin'):
                torch.compiler.cudagraph_mark_step_begin()
                torch.cuda.synchronize()
            
            # Call the original get_control
            result = original_get_control(self, x_noisy, t, cond, batched_number, transformer_options)
            
            try:
                # If result is None (e.g., due to timestep range), return early
                if result is None:
                    return None
                
                # Deep clone the result to ensure independence for CUDA graphs
                result = {
                    k: [t.clone() if t is not None else None for t in v]
                    for k, v in result.items()
                }
                return result
            except Exception as e:
                print(f"Error: Failed to clone ControlNet output in get_control: {str(e)}")
                raise e
            finally:
                # Mark CUDA graph step at end, even if an error occurs
                if torch.cuda.is_available() and hasattr(torch.compiler, 'cudagraph_mark_step_begin'):
                    torch.compiler.cudagraph_mark_step_begin()
                    torch.cuda.synchronize()
        
        # Apply the patch
        ControlNet.get_control = wrapped_get_control
        print("Successfully patched ControlNet.get_control for torch.compile() compatibility")
    except Exception as e:
        print(f"Warning: Failed to patch ControlNet: {str(e)}")

# Apply patch when module is imported
patch_controlnet_for_stream()