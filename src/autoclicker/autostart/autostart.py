"""Enable or disable launching the app at system startup.

- Windows : HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
- Linux   : ~/.config/autostart/<app>.desktop
- macOS   : ~/Library/LaunchAgents/<app>.plist
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "MyTimeAutoclicker"


def _get_executable() -> str:
    """Return the path to the running executable or python + script."""
    if getattr(sys, "frozen", False):
        return sys.executable
    # Running as a plain Python script
    script = Path(__file__).resolve().parents[3] / "main.py"
    return f'"{sys.executable}" "{script}"'


# ── Windows ──────────────────────────────────────────────────────────────────

def _win_enable(exe: str) -> None:
    import winreg  # noqa: PLC0415  (Windows-only)
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, exe)
    logger.info("Autostart enabled via registry")


def _win_disable() -> None:
    import winreg  # noqa: PLC0415
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, APP_NAME)
        logger.info("Autostart disabled (registry entry removed)")
    except FileNotFoundError:
        pass


# ── Linux ────────────────────────────────────────────────────────────────────

def _linux_desktop_path() -> Path:
    autostart_dir = Path(
        os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    ) / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    return autostart_dir / f"{APP_NAME}.desktop"


def _linux_enable(exe: str) -> None:
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={exe}\n"
        "Hidden=false\n"
        "NoDisplay=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    _linux_desktop_path().write_text(content, encoding="utf-8")
    logger.info("Autostart enabled via .desktop file")


def _linux_disable() -> None:
    path = _linux_desktop_path()
    if path.exists():
        path.unlink()
        logger.info("Autostart disabled (.desktop file removed)")


# ── macOS ────────────────────────────────────────────────────────────────────

def _macos_plist_path() -> Path:
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    return launch_agents / f"com.{APP_NAME.lower()}.plist"


def _macos_enable(exe: str) -> None:
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f'  <key>Label</key><string>com.{APP_NAME.lower()}</string>\n'
        f'  <key>ProgramArguments</key><array><string>{exe}</string></array>\n'
        '  <key>RunAtLoad</key><true/>\n'
        '</dict></plist>\n'
    )
    _macos_plist_path().write_text(plist, encoding="utf-8")
    logger.info("Autostart enabled via LaunchAgent plist")


def _macos_disable() -> None:
    path = _macos_plist_path()
    if path.exists():
        path.unlink()
        logger.info("Autostart disabled (plist removed)")


# ── Public API ────────────────────────────────────────────────────────────────

def enable_autostart() -> None:
    exe = _get_executable()
    if sys.platform == "win32":
        _win_enable(exe)
    elif sys.platform == "darwin":
        _macos_enable(exe)
    else:
        _linux_enable(exe)


def disable_autostart() -> None:
    if sys.platform == "win32":
        _win_disable()
    elif sys.platform == "darwin":
        _macos_disable()
    else:
        _linux_disable()


def set_autostart(enabled: bool) -> None:
    if enabled:
        enable_autostart()
    else:
        disable_autostart()
