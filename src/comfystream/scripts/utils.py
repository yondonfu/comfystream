import yaml
from pathlib import Path


def get_config_path(filename):
    """Get the absolute path to a config file"""
    config_path = Path("configs") / filename
    if not config_path.exists():
        print(f"Warning: Config file {filename} not found at {config_path}")
        print(f"Available files in configs/:")
        try:
            for f in Path("configs").glob("*"):
                print(f"  - {f.name}")
        except FileNotFoundError:
            print("  configs/ directory not found")
        raise FileNotFoundError(f"Config file {filename} not found at {config_path}")
    return config_path


def load_model_config(config_path):
    """Load model configuration from YAML file"""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
