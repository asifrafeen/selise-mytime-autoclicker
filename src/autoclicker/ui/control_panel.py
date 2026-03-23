"""Control panel — a small popup window with a Test Run button and status."""

import logging
import threading
import tkinter as tk
from typing import Callable

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

logger = logging.getLogger(__name__)

_panel: "ControlPanel | None" = None


class ControlPanel(ttk.Toplevel):
    def __init__(self, parent, on_run_now: Callable, on_show_settings: Callable):
        super().__init__(parent)
        self.title("MyTime Autoclicker")
        self.resizable(False, False)
        self._on_run_now = on_run_now
        self._on_show_settings = on_show_settings
        self._running = False

        self._build_ui()
        self._center()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.lift()
        self.focus_force()

    def _build_ui(self) -> None:
        # Header
        header = ttk.Frame(self, bootstyle="primary")
        header.pack(fill=X)
        ttk.Label(
            header,
            text="  MyTime Autoclicker",
            font=("Segoe UI", 12, "bold"),
            bootstyle="inverse-primary",
        ).pack(side=LEFT, pady=10, padx=4)

        body = ttk.Frame(self, padding=(24, 16))
        body.pack(fill=BOTH, expand=True)

        # Schedule info
        ttk.Label(
            body,
            text="Runs automatically Mon–Thu & Sun",
            font=("Segoe UI", 9),
            foreground="gray",
        ).pack(anchor=W)

        ttk.Separator(body).pack(fill=X, pady=12)

        # Status indicator
        status_frame = ttk.Frame(body)
        status_frame.pack(fill=X, pady=(0, 12))
        ttk.Label(status_frame, text="Status:", font=("Segoe UI", 9, "bold")).pack(side=LEFT)
        self._status_var = tk.StringVar(value="Idle")
        self._status_label = ttk.Label(
            status_frame,
            textvariable=self._status_var,
            font=("Segoe UI", 9),
            bootstyle="success",
        )
        self._status_label.pack(side=LEFT, padx=8)

        # Test Run button (prominent)
        self._run_btn = ttk.Button(
            body,
            text="▶  Test Run Now",
            bootstyle="success",
            width=22,
            command=self._trigger_run,
        )
        self._run_btn.pack(pady=(0, 8), ipady=6)

        # Settings button
        ttk.Button(
            body,
            text="⚙  Settings",
            bootstyle="secondary-outline",
            width=22,
            command=self._open_settings,
        ).pack(ipady=3)

    def _trigger_run(self) -> None:
        if self._running:
            return
        self._running = True
        self._run_btn.configure(state=DISABLED, text="Running…")
        self._status_var.set("Running…")
        self._status_label.configure(bootstyle="warning")

        def _job():
            try:
                self._on_run_now()
            finally:
                # Update UI back on main thread
                self.after(0, self._on_run_finished)

        threading.Thread(target=_job, daemon=True, name="test-run").start()

    def _on_run_finished(self) -> None:
        self._running = False
        try:
            self._run_btn.configure(state=NORMAL, text="▶  Test Run Now")
            self._status_var.set("Completed")
            self._status_label.configure(bootstyle="success")
        except tk.TclError:
            pass  # Window was closed while running

    def _open_settings(self) -> None:
        self.destroy()
        self._on_show_settings()

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


def show_control_panel(parent, on_run_now: Callable, on_show_settings: Callable) -> None:
    global _panel
    if _panel is not None:
        try:
            _panel.lift()
            _panel.focus_force()
            return
        except tk.TclError:
            pass
    _panel = ControlPanel(parent, on_run_now, on_show_settings)
    _panel.bind("<Destroy>", lambda _: _clear_ref())


def _clear_ref() -> None:
    global _panel
    _panel = None
