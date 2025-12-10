"""BYOC-specific utilities that depend on pytrickle.

This module contains utilities that are only needed for the BYOC (Bring Your Own Compute)
server implementation and require pytrickle as a dependency.
"""

import json

# Import from core utils to avoid duplication
import sys
from pathlib import Path
from typing import Any, Dict

from pytrickle.api import StreamParamsUpdateRequest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from comfystream.utils import convert_prompt


class ComfyStreamParamsUpdateRequest(StreamParamsUpdateRequest):
    """ComfyStream parameter validation."""

    def __init__(self, **data):
        # Handle prompts parameter
        if "prompts" in data:
            prompts = data["prompts"]

            # Parse JSON string if needed
            if isinstance(prompts, str) and prompts.strip():
                try:
                    prompts = json.loads(prompts)
                except json.JSONDecodeError:
                    data.pop("prompts")

            # Handle list - use first valid dict
            elif isinstance(prompts, list):
                prompts = next((p for p in prompts if isinstance(p, dict)), None)
                if not prompts:
                    data.pop("prompts")

            # Validate prompts
            if "prompts" in data and isinstance(prompts, dict):
                try:
                    data["prompts"] = convert_prompt(prompts, return_dict=True)
                except Exception:
                    data.pop("prompts")

        # Call parent constructor
        super().__init__(**data)

    @classmethod
    def model_validate(cls, obj):
        return cls(**obj)

    def model_dump(self):
        return super().model_dump()


def normalize_stream_params(params: Any) -> Dict[str, Any]:
    """Normalize stream parameters from various formats to a dict.

    Args:
        params: Parameters in dict, list, or other format

    Returns:
        Dict containing normalized parameters, empty dict if invalid
    """
    if params is None:
        return {}
    if isinstance(params, dict):
        return dict(params)
    if isinstance(params, list):
        for candidate in params:
            if isinstance(candidate, dict):
                return dict(candidate)
        return {}
    return {}
