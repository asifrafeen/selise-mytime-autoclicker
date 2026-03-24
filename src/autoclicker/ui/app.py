"""Application bootstrap.

Creates the main window (always visible), runs setup wizard on first launch,
then starts the scheduler and tray icon.
"""

import logging
import threading

from autoclicker.config.credentials import load_credentials, credentials_exist
from autoclicker.config.settings import load_settings, is_setup_complete
from autoclicker.automation.timesheet import run_timesheet
from autoclicker import scheduler, tray
from autoclicker.ui.wizard import SetupWizard
from autoclicker.ui.main_window import MainWindow

logger = logging.getLogger(__name__)

_window: MainWindow | None = None
_run_thread: threading.Thread | None = None


def create_and_run(register_signal_fn=None) -> None:
    """Entry point — creates window, bootstraps app, starts mainloop."""
    global _window

    _window = MainWindow(on_run_now=_run_automation, on_reschedule=_reschedule)

    # Register SIGUSR1 handler so a second invocation can raise this window
    if register_signal_fn is not None:
        register_signal_fn(_window)

    if not is_setup_complete() or not credentials_exist():
        logger.info("First run - showing setup wizard")
        SetupWizard(_window, on_complete=lambda: _start_background(_window))
    else:
        _start_background(_window)

    _window.mainloop()


def _start_background(window: MainWindow) -> None:
    settings = load_settings()
    hour, minute = settings["run_hour"], settings["run_minute"]

    scheduler.start(lambda: _run_automation(), hour, minute)

    tray.start_tray(
        on_show_settings=window.deiconify,   # re-show the main window
        on_show_panel=window.deiconify,
        on_run_now=_run_automation,
        on_quit=lambda: _quit(window),
        root=window,
    )

    # Refresh the window display now that credentials are saved
    window.after(0, window._refresh_config)
    logger.info("App started - scheduled at %02d:%02d", hour, minute)


def _run_automation() -> None:
    global _run_thread
    if _run_thread and _run_thread.is_alive():
        logger.warning("Automation already running - skipping")
        return

    settings = load_settings()
    try:
        username, password = load_credentials()
    except FileNotFoundError:
        logger.error("No credentials found - skipping run")
        return

    def _job():
        run_timesheet(username, password, headless=settings.get("headless", True))

    _run_thread = threading.Thread(target=_job, daemon=True, name="playwright-job")
    _run_thread.start()


def _reschedule(hour: int, minute: int) -> None:
    scheduler.reschedule(lambda: _run_automation(), hour, minute)


def _quit(window: MainWindow) -> None:
    logger.info("Quit requested")
    scheduler.stop()
    tray.stop_tray()
    window.destroy()
