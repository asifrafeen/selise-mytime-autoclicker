"""System tray icon using pystray.

All callbacks that touch the tkinter GUI must use root.after() because
tkinter is not thread-safe — only the main thread may call tk methods.
"""

import logging
import threading
from pathlib import Path
from typing import Callable

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

_tray_icon: pystray.Icon | None = None


def _create_icon_image() -> Image.Image:
    """Generate a simple clock-like icon programmatically."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Circle background
    draw.ellipse([2, 2, size - 2, size - 2], fill="#2563EB")
    # Clock hands (simple)
    cx, cy = size // 2, size // 2
    draw.line([cx, cy, cx, cy - 18], fill="white", width=3)  # hour hand
    draw.line([cx, cy, cx + 14, cy], fill="white", width=2)  # minute hand
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill="white")
    return img


def _load_icon_image() -> Image.Image:
    icon_path = Path(__file__).resolve().parents[4] / "assets" / "icon.png"
    if icon_path.exists():
        return Image.open(icon_path).convert("RGBA")
    return _create_icon_image()


def start_tray(
    on_show_settings: Callable,
    on_show_panel: Callable,
    on_run_now: Callable,
    on_quit: Callable,
    root,  # tkinter root — used for root.after() bridging
) -> None:
    """Create and start the tray icon in a background daemon thread."""

    def _post(fn: Callable) -> Callable:
        """Wrap a callback so it executes on the tk main thread."""
        def wrapper(*args):
            root.after(0, fn)
        return wrapper

    menu = pystray.Menu(
        # Default item (bold, activated on left-click / double-click)
        pystray.MenuItem("Open…", _post(on_show_panel), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Run Now", _post(on_run_now)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Settings…", _post(on_show_settings)),
        pystray.MenuItem("View Logs…", _post(_open_logs)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _post(on_quit)),
    )

    global _tray_icon
    _tray_icon = pystray.Icon(
        "MyTimeAutoclicker",
        _load_icon_image(),
        "MyTime Autoclicker",
        menu,
    )

    thread = threading.Thread(target=_tray_icon.run, daemon=True, name="tray-thread")
    thread.start()
    logger.info("System tray icon started")


def stop_tray() -> None:
    global _tray_icon
    if _tray_icon is not None:
        _tray_icon.stop()
        _tray_icon = None


def _open_logs() -> None:
    import os
    import sys
    from autoclicker.logging_setup import get_log_file_path

    log_path = get_log_file_path()
    if sys.platform == "win32":
        os.startfile(log_path)
    elif sys.platform == "darwin":
        os.system(f'open "{log_path}"')
    else:
        os.system(f'xdg-open "{log_path}"')
