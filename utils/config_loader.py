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
        config_path = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"
        with open(config_path, "r") as f:
            _config_cache = yaml.safe_load(f)
    
    return _config_cache

def get_config_value(key: str, default=None):
    """Get a specific value from configuration."""
    config = load_config()
    return config.get(key, default)