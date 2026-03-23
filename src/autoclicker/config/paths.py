"""Platform-aware application data directory resolution."""

import os
import sys
from pathlib import Path

APP_NAME = "MyTimeAutoclicker"


def get_appdata_dir() -> Path:
    """Return the platform-appropriate directory for storing app data."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux / XDG
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_logs_dir() -> Path:
    log_dir = get_appdata_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_settings_path() -> Path:
    return get_appdata_dir() / "settings.json"


def get_credentials_path() -> Path:
    return get_appdata_dir() / "credentials.enc"
