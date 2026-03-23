"""Application window manager.

Owns the single tkinter root. All background threads communicate back
to tk via root.after() — never directly.
"""

import logging
import threading

import ttkbootstrap as ttk

from autoclicker.config.credentials import load_credentials, credentials_exist
from autoclicker.config.settings import load_settings, is_setup_complete
from autoclicker.automation.timesheet import run_timesheet
from autoclicker import scheduler, tray
from autoclicker.ui.wizard import SetupWizard
from autoclicker.ui.settings_window import show_settings

logger = logging.getLogger(__name__)

_root: ttk.Window | None = None
_run_thread: threading.Thread | None = None


def create_root() -> ttk.Window:
    global _root
    _root = ttk.Window(themename="cosmo")
    _root.withdraw()  # Hidden — lives only in the tray
    _root.title("MyTime Autoclicker")
    _root.protocol("WM_DELETE_WINDOW", _root.withdraw)  # Hide instead of close
    return _root


def bootstrap(root: ttk.Window) -> None:
    """Run setup wizard if first launch, otherwise start full app."""
    if not is_setup_complete() or not credentials_exist():
        logger.info("First run detected — showing setup wizard")
        SetupWizard(root, on_complete=lambda: _start_app(root))
    else:
        _start_app(root)


def _start_app(root: ttk.Window) -> None:
    settings = load_settings()
    hour = settings["run_hour"]
    minute = settings["run_minute"]

    def job():
        _run_automation()

    # Start scheduler
    scheduler.start(job, hour, minute)

    # Start tray
    tray.start_tray(
        on_show_settings=lambda: show_settings(root, _reschedule, _run_now),
        on_run_now=_run_now,
        on_quit=lambda: _quit(root),
        root=root,
    )

    logger.info("App started. Scheduled at %02d:%02d", hour, minute)


def _run_automation() -> None:
    global _run_thread
    if _run_thread and _run_thread.is_alive():
        logger.warning("Automation already running — skipping")
        return

    settings = load_settings()
    try:
        username, password = load_credentials()
    except FileNotFoundError:
        logger.error("No credentials found — skipping run")
        return

    def _job():
        try:
            run_timesheet(username, password, headless=settings.get("headless", True))
        except Exception:
            logger.exception("Automation run failed")

    _run_thread = threading.Thread(target=_job, daemon=True, name="playwright-job")
    _run_thread.start()


def _run_now() -> None:
    logger.info("Manual run triggered")
    _run_automation()


def _reschedule(hour: int, minute: int) -> None:
    settings = load_settings()
    scheduler.reschedule(
        lambda: _run_automation(),
        hour,
        minute,
    )


def _quit(root: ttk.Window) -> None:
    logger.info("Quit requested")
    scheduler.stop()
    tray.stop_tray()
    root.destroy()
