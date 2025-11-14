"""
Persistent device configuration helpers for classroom-scoped deployments.
"""

import json
import os
from typing import Dict

DEFAULT_CONFIG = {
    "classroom_id": "",
    "classroom_label": "",
    "teacher_name": "",
}

CONFIG_FILENAME = "device_config.json"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)


def _ensure_all_keys(config: Dict[str, str]) -> Dict[str, str]:
    """Ensure the config dict has all expected keys."""
    normalized = DEFAULT_CONFIG.copy()
    normalized.update({k: v for k, v in config.items() if k in DEFAULT_CONFIG})
    return normalized


def load_device_config() -> Dict[str, str]:
    """
    Load the classroom configuration from disk.

    Returns the default configuration if the file does not exist or cannot be read.
    """
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
            if isinstance(data, dict):
                return _ensure_all_keys(data)
            return DEFAULT_CONFIG.copy()
    except Exception as err:
        print(f"[DEVICE-CONFIG] Error loading config: {err}")
        return DEFAULT_CONFIG.copy()


def save_device_config(config: Dict[str, str]) -> None:
    """Persist the classroom configuration to disk."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    normalized = _ensure_all_keys(config)

    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
            json.dump(normalized, config_file, indent=2)
        print(f"[DEVICE-CONFIG] Saved configuration to {CONFIG_PATH}")
    except Exception as err:
        print(f"[DEVICE-CONFIG] Error saving config: {err}")


def update_device_config(**updates) -> Dict[str, str]:
    """
    Convenience helper to update and persist selected fields.

    Returns the updated configuration dict.
    """
    config = load_device_config()
    for key, value in updates.items():
        if key in DEFAULT_CONFIG:
            config[key] = value
    save_device_config(config)
    return config

