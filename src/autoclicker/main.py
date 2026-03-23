"""Application entry point.

Sets up Playwright browser path for frozen (PyInstaller) builds,
enforces single-instance via a lock file, initialises logging,
then hands control to the UI layer.

Single-instance behaviour:
  - First launch acquires a lock file and writes its PID.
  - Subsequent launches read that PID, send SIGUSR1 to the running process
    (which brings its window to the front), then exit immediately.
"""

import os
import signal
import sys
from pathlib import Path

# ── Allow running directly as `python src/autoclicker/main.py` ───────────────
_src = str(Path(__file__).resolve().parents[2])
if _src not in sys.path:
    sys.path.insert(0, _src)

# ── Frozen-app browser path fix (must run before any playwright import) ──────
if getattr(sys, "frozen", False):
    _browsers_path = os.path.join(os.path.dirname(sys.executable), "_playwright_browsers")
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", _browsers_path)

from autoclicker.logging_setup import setup_logging  # noqa: E402
from autoclicker.ui.app import create_and_run        # noqa: E402
from autoclicker.config.paths import get_appdata_dir # noqa: E402


def _lock_path() -> Path:
    return get_appdata_dir() / "app.lock"


def _acquire_lock():
    """Try to acquire an exclusive lock. Returns file handle on success, None if already locked."""
    path = _lock_path()

    if sys.platform == "win32":
        import msvcrt
        try:
            fh = open(path, "a+")
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            fh.seek(0); fh.truncate()
            fh.write(str(os.getpid())); fh.flush()
            return fh
        except OSError:
            fh.close()
            return None
    else:
        import fcntl
        fh = open(path, "a+")  # "a+" does not truncate — preserves existing PID until we own the lock
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # We own the lock — now safe to overwrite with our PID
            fh.seek(0); fh.truncate()
            fh.write(str(os.getpid())); fh.flush()
            return fh
        except OSError:
            fh.close()
            return None


def _signal_existing_instance() -> None:
    """Read PID from lock file and send SIGUSR1 to bring its window forward."""
    try:
        pid_str = _lock_path().read_text().strip()
        if not pid_str:
            print("Stale lock file — delete it and relaunch.")
            _lock_path().unlink(missing_ok=True)
            return
        pid = int(pid_str)
        os.kill(pid, signal.SIGUSR1)
        print(f"Signalled existing instance (PID {pid}) to show window.")
    except Exception as exc:
        print(f"Could not signal existing instance: {exc}")


_show_requested = False


def _register_show_signal(window) -> None:
    """Register SIGUSR1 handler + a polling loop to safely show the window."""
    if sys.platform == "win32":
        return  # SIGUSR1 not available on Windows

    def _handler(signum, frame):
        # Signal handlers must not call tk directly — just set a flag
        global _show_requested
        _show_requested = True

    signal.signal(signal.SIGUSR1, _handler)

    # Hide window on suspend (Ctrl+Z), restore on resume
    def _on_suspend(signum, frame):
        global _show_requested
        window.after(0, window.withdraw)

    def _on_resume(signum, frame):
        global _show_requested
        _show_requested = True

    signal.signal(signal.SIGTSTP, _on_suspend)
    signal.signal(signal.SIGCONT, _on_resume)

    # Poll every 250 ms — when flag is set, bring window forward
    def _poll():
        global _show_requested
        if _show_requested:
            _show_requested = False
            window.deiconify()
            window.state("normal")
            window.lift()
            window.focus_force()
        window.after(250, _poll)

    window.after(250, _poll)


def main() -> None:
    lock = _acquire_lock()

    if lock is None:
        # Another instance is running — signal it to show its window
        _signal_existing_instance()
        sys.exit(0)

    try:
        setup_logging()
        window = create_and_run(register_signal_fn=_register_show_signal)  # noqa: F841
    finally:
        lock.close()


if __name__ == "__main__":
    main()
