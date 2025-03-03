import os
import sys
import importlib.util


#we use importlib as prestartup_script.py is not executed as part of the package
# Get the current directory path
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the tensor_utils prestartup_script.py
tensor_utils_script_path = os.path.join(current_dir, "nodes", "tensor_utils", "prestartup_script.py")

# Load and execute the script directly
spec = importlib.util.spec_from_file_location("tensor_utils_prestartup", tensor_utils_script_path)
tensor_utils_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tensor_utils_module)

print("Main prestartup_script.py loaded and executed tensor_utils version") 