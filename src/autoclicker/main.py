"""Application entry point.

Single-instance + cross-platform IPC via a local TCP socket:
  - First launch binds the IPC port  → becomes the primary instance.
  - Subsequent launches connect to it → send "SHOW", then exit.
  - The primary instance receives "SHOW" and raises its window.

This works identically on Windows, macOS, and Linux without any
platform-specific locking (no fcntl, no msvcrt, no SIGUSR1).
"""

import os
import signal
import socket
import sys
import threading
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

# ── IPC constants ─────────────────────────────────────────────────────────────
_IPC_HOST = "127.0.0.1"
_IPC_PORT = 47_381          # arbitrary app-specific port
_IPC_MSG_SHOW = b"SHOW"

_show_requested = False
_ipc_server_sock: socket.socket | None = None


# ── Single-instance check ─────────────────────────────────────────────────────

def _try_become_primary() -> bool:
    """
    Try to bind the IPC port.
    Returns True  → we are the first (primary) instance.
    Returns False → another instance already owns the port.
    """
    global _ipc_server_sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((_IPC_HOST, _IPC_PORT))
        sock.listen(5)
        _ipc_server_sock = sock
        return True
    except OSError:
        sock.close()
        return False


def _signal_existing_instance() -> None:
    """Connect to the running instance and ask it to show its window."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((_IPC_HOST, _IPC_PORT))
            s.sendall(_IPC_MSG_SHOW)
        print("MyTime Autoclicker is already running — bringing window to front.")
    except Exception as exc:
        print(f"Could not reach existing instance: {exc}")
        print("If the app is not visible, try restarting it.")


# ── IPC server (runs in background thread of primary instance) ────────────────

def _start_ipc_listener() -> None:
    """Accept SHOW commands from secondary instances (daemon thread)."""
    def _serve() -> None:
        global _show_requested, _ipc_server_sock
        if _ipc_server_sock is None:
            return
        _ipc_server_sock.settimeout(1.0)
        while True:
            try:
                conn, _ = _ipc_server_sock.accept()
                with conn:
                    data = conn.recv(16)
                    if data == _IPC_MSG_SHOW:
                        _show_requested = True
            except socket.timeout:
                continue
            except OSError:
                break  # socket closed on app exit

    threading.Thread(target=_serve, daemon=True, name="ipc-server").start()


# ── Window show-request polling (runs on tk main thread) ─────────────────────

def _register_show_handler(window) -> None:
    """
    Poll every 250 ms for a show request set by the IPC listener thread.
    Also wires up Unix suspend/resume signals where available.
    """
    global _show_requested

    # Unix: hide on Ctrl+Z suspend, restore on fg/SIGCONT
    if hasattr(signal, "SIGTSTP"):
        def _on_suspend(signum, frame):
            window.after(0, window.withdraw)
        signal.signal(signal.SIGTSTP, _on_suspend)

    if hasattr(signal, "SIGCONT"):
        def _on_resume(signum, frame):
            global _show_requested
            _show_requested = True
        signal.signal(signal.SIGCONT, _on_resume)

    def _poll() -> None:
        global _show_requested
        if _show_requested:
            _show_requested = False
            window.deiconify()
            window.state("normal")
            window.lift()
            window.focus_force()
        window.after(250, _poll)

    window.after(250, _poll)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not _try_become_primary():
        # Another instance is running — signal it and exit
        _signal_existing_instance()
        sys.exit(0)

    # We are the primary instance
    _start_ipc_listener()

    try:
        setup_logging()
        create_and_run(register_signal_fn=_register_show_handler)
    finally:
        # Release the IPC port on exit
        if _ipc_server_sock:
            _ipc_server_sock.close()


if __name__ == "__main__":
    main()
