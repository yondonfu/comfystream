# Point to the directory containing our web files
WEB_DIRECTORY = "./nodes/web/js"

# Import and expose node classes
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
