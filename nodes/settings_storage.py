"""ComfyStream server-side settings storage module"""
import os
import json
import logging
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[ComfyStream Settings] %(message)s'
)

# Default settings
DEFAULT_SETTINGS = {
    "host": "0.0.0.0",
    "port": 8889,
    "configurations": [],
    "selectedConfigIndex": -1
}

# Lock for thread-safe file operations
settings_lock = threading.Lock()

def get_settings_file_path():
    """Get the path to the settings file"""
    # Store settings in the extension directory
    extension_dir = Path(__file__).parent.parent
    settings_dir = extension_dir / "settings"
    
    # Create settings directory if it doesn't exist
    os.makedirs(settings_dir, exist_ok=True)
    
    return settings_dir / "comfystream_settings.json"

def load_settings():
    """Load settings from file"""
    settings_file = get_settings_file_path()
    
    with settings_lock:
        try:
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    
                    # Ensure all default keys exist
                    for key, value in DEFAULT_SETTINGS.items():
                        if key not in settings:
                            settings[key] = value
                    
                    return settings
            else:
                return DEFAULT_SETTINGS.copy()
        except Exception as e:
            logging.error(f"Error loading settings: {str(e)}")
            return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to file"""
    settings_file = get_settings_file_path()
    
    with settings_lock:
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error saving settings: {str(e)}")
            return False

def update_settings(new_settings):
    """Update settings with new values"""
    current_settings = load_settings()
    
    # Update only the keys that are provided
    for key, value in new_settings.items():
        current_settings[key] = value
    
    return save_settings(current_settings)

def add_configuration(name, host, port):
    """Add a new configuration"""
    settings = load_settings()
    
    # Create the new configuration
    config = {"name": name, "host": host, "port": port}
    
    # Add to configurations list
    settings["configurations"].append(config)
    
    # Save updated settings
    return save_settings(settings)

def remove_configuration(index):
    """Remove a configuration by index"""
    settings = load_settings()
    
    if index < 0 or index >= len(settings["configurations"]):
        logging.error(f"Invalid configuration index: {index}")
        return False
    
    # Remove the configuration
    settings["configurations"].pop(index)
    
    # Update selectedConfigIndex if needed
    if settings["selectedConfigIndex"] == index:
        # The selected config was deleted
        settings["selectedConfigIndex"] = -1
    elif settings["selectedConfigIndex"] > index:
        # The selected config is after the deleted one, adjust index
        settings["selectedConfigIndex"] -= 1
    
    # Save updated settings
    return save_settings(settings)

def select_configuration(index):
    """Select a configuration by index"""
    settings = load_settings()
    
    if index == -1 or (index >= 0 and index < len(settings["configurations"])):
        settings["selectedConfigIndex"] = index
        
        # If a valid configuration is selected, update host and port
        if index >= 0:
            config = settings["configurations"][index]
            settings["host"] = config["host"]
            settings["port"] = config["port"]
        
        # Save updated settings
        return save_settings(settings)
    else:
        logging.error(f"Invalid configuration index: {index}")
        return False 