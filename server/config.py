import tomli
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ComfyConfig:
    def __init__(self, config_path: Optional[str] = None):
        self.servers = []
        self.config_path = config_path
        if config_path:
            self.load_config(config_path)
        else:
            # Default to single local server if no config provided
            self.servers = [{"host": "127.0.0.1", "port": 8188}]
            
    def load_config(self, config_path: str):
        """Load server configuration from TOML file"""
        try:
            with open(config_path, "rb") as f:
                config = tomli.load(f)
            
            # Extract server configurations
            if "servers" in config:
                self.servers = config["servers"]
                logger.info(f"Loaded {len(self.servers)} server configurations")
            else:
                logger.warning("No servers defined in config, using default")
                self.servers = [{"host": "127.0.0.1", "port": 8198}]
                
            # Validate each server has required fields
            for i, server in enumerate(self.servers):
                if "host" not in server or "port" not in server:
                    logger.warning(f"Server {i} missing host or port, using defaults")
                    server["host"] = server.get("host", "127.0.0.1")
                    server["port"] = server.get("port", 8198)
                
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            # Fall back to default server
            self.servers = [{"host": "127.0.0.1", "port": 8198}]
    
    def get_servers(self) -> List[Dict[str, Any]]:
        """Return list of server configurations"""
        return self.servers 