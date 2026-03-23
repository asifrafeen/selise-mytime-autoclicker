"""Read and write application settings from/to settings.json."""

import json
from typing import Any

from .paths import get_settings_path

_DEFAULTS: dict[str, Any] = {
    "run_hour": 9,
    "run_minute": 0,
    "autostart_enabled": False,
    "headless": True,
    "setup_complete": False,
}


def load_settings() -> dict[str, Any]:
    path = get_settings_path()
    if not path.exists():
        return dict(_DEFAULTS)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Merge with defaults so new keys are always present
    merged = dict(_DEFAULTS)
    merged.update(data)
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    path = get_settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def is_setup_complete() -> bool:
    return load_settings().get("setup_complete", False)
