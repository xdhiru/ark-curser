"""
Shared configuration loader to avoid duplicate code.
"""

import yaml
from pathlib import Path

# Cache loaded config
_config_cache = None

def load_config() -> dict:
    """Load configuration from settings.yaml with caching."""
    global _config_cache
    
    if _config_cache is None:
        # Resolve path relative to this file
        config_path = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"
        try:
            with open(config_path, "r") as f:
                _config_cache = yaml.safe_load(f)
        except Exception as e:
            # Fallback for safety if file is missing/corrupt
            print(f"CRITICAL ERROR loading config: {e}")
            _config_cache = {}
    
    return _config_cache

def get_config_value(key: str, default=None):
    """
    Get a specific value from configuration using dot notation.
    Example: get_config_value("adaptive_waits.max_retries")
    """
    config = load_config()
    
    # Handle dot notation for nested keys
    if "." in key:
        keys = key.split(".")
        value = config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            # Key not found or path invalid
            return default
            
    # Handle top-level keys
    return config.get(key, default)