"""Settings window — update credentials, schedule, autostart, manual run."""

import logging
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from autoclicker.config.credentials import load_credentials, save_credentials
from autoclicker.config.settings import load_settings, save_settings
from autoclicker.autostart.autostart import set_autostart

logger = logging.getLogger(__name__)

_settings_window: "SettingsWindow | None" = None


class SettingsWindow(ttk.Toplevel):
    def __init__(self, parent, on_reschedule: Callable, on_run_now: Callable):
        super().__init__(parent)
        self.title("MyTime Autoclicker — Settings")
        self.resizable(False, False)
        self._on_reschedule = on_reschedule
        self._on_run_now = on_run_now

        self._load_current()
        self._build_ui()
        self._center()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ── Data ─────────────────────────────────────────────────────────────────

    def _load_current(self) -> None:
        self._settings = load_settings()
        try:
            self._current_user, self._current_pass = load_credentials()
        except FileNotFoundError:
            self._current_user, self._current_pass = "", ""

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 20, "pady": 8}

        # Header
        header = ttk.Frame(self, bootstyle="primary")
        header.pack(fill=X)
        ttk.Label(
            header,
            text="  Settings",
            font=("Segoe UI", 13, "bold"),
            bootstyle="inverse-primary",
        ).pack(side=LEFT, pady=10)

        body = ttk.Frame(self, padding=20)
        body.pack(fill=BOTH, expand=True)

        # ── Credentials ──────────────────────────────────────────────────
        ttk.Label(body, text="Credentials", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=W, pady=(0, 4)
        )

        ttk.Label(body, text="Username:").grid(row=1, column=0, sticky=W, **pad)
        self._username_var = tk.StringVar(value=self._current_user)
        ttk.Entry(body, textvariable=self._username_var, width=32).grid(
            row=1, column=1, sticky=EW, **pad
        )

        ttk.Label(body, text="Password:").grid(row=2, column=0, sticky=W, **pad)
        self._password_var = tk.StringVar(value=self._current_pass)
        self._pw_entry = ttk.Entry(body, textvariable=self._password_var, show="•", width=32)
        self._pw_entry.grid(row=2, column=1, sticky=EW, **pad)

        self._show_pw = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            body, text="Show password", variable=self._show_pw,
            command=self._toggle_pw, bootstyle="round-toggle"
        ).grid(row=3, column=1, sticky=W, padx=20)

        ttk.Separator(body).grid(row=4, column=0, columnspan=2, sticky=EW, pady=12)

        # ── Schedule ─────────────────────────────────────────────────────
        ttk.Label(body, text="Schedule", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=0, columnspan=2, sticky=W, pady=(0, 4)
        )

        ttk.Label(body, text="Run daily at:").grid(row=6, column=0, sticky=W, **pad)
        time_frame = ttk.Frame(body)
        time_frame.grid(row=6, column=1, sticky=W, **pad)

        self._hour_var = tk.StringVar(value=f"{self._settings['run_hour']:02d}")
        self._minute_var = tk.StringVar(value=f"{self._settings['run_minute']:02d}")
        ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self._hour_var,
                    width=4, format="%02.0f").pack(side=LEFT)
        ttk.Label(time_frame, text=" : ").pack(side=LEFT)
        ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self._minute_var,
                    width=4, format="%02.0f").pack(side=LEFT)
        ttk.Label(time_frame, text="  Mon–Thu & Sun", foreground="gray").pack(side=LEFT)

        ttk.Separator(body).grid(row=7, column=0, columnspan=2, sticky=EW, pady=12)

        # ── Options ──────────────────────────────────────────────────────
        ttk.Label(body, text="Options", font=("Segoe UI", 10, "bold")).grid(
            row=8, column=0, columnspan=2, sticky=W, pady=(0, 4)
        )

        self._autostart_var = tk.BooleanVar(value=self._settings.get("autostart_enabled", False))
        ttk.Checkbutton(
            body, text="Launch at system startup",
            variable=self._autostart_var, bootstyle="round-toggle"
        ).grid(row=9, column=0, columnspan=2, sticky=W, padx=20, pady=4)

        self._headless_var = tk.BooleanVar(value=self._settings.get("headless", True))
        ttk.Checkbutton(
            body, text="Run browser in headless mode (background)",
            variable=self._headless_var, bootstyle="round-toggle"
        ).grid(row=10, column=0, columnspan=2, sticky=W, padx=20, pady=4)

        ttk.Separator(body).grid(row=11, column=0, columnspan=2, sticky=EW, pady=12)

        # ── Buttons ──────────────────────────────────────────────────────
        btn_frame = ttk.Frame(body)
        btn_frame.grid(row=12, column=0, columnspan=2, pady=(4, 0))

        ttk.Button(btn_frame, text="Run Now", bootstyle="info",
                   command=self._run_now).pack(side=LEFT, padx=4)
        ttk.Button(btn_frame, text="Save", bootstyle="success",
                   command=self._save).pack(side=RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", bootstyle="secondary",
                   command=self.destroy).pack(side=RIGHT, padx=4)

        body.columnconfigure(1, weight=1)

        # ── Status bar ───────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._status_var, bootstyle="secondary",
                  font=("Segoe UI", 9)).pack(side=BOTTOM, anchor=W, padx=16, pady=4)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _toggle_pw(self) -> None:
        self._pw_entry.configure(show="" if self._show_pw.get() else "•")

    def _save(self) -> None:
        username = self._username_var.get().strip()
        password = self._password_var.get()
        if not username or not password:
            messagebox.showerror("Validation", "Username and password are required.", parent=self)
            return

        try:
            hour = int(self._hour_var.get())
            minute = int(self._minute_var.get())
        except ValueError:
            messagebox.showerror("Validation", "Run time must be numeric.", parent=self)
            return

        try:
            save_credentials(username, password)
            self._settings["run_hour"] = hour
            self._settings["run_minute"] = minute
            self._settings["autostart_enabled"] = self._autostart_var.get()
            self._settings["headless"] = self._headless_var.get()
            save_settings(self._settings)
            set_autostart(self._autostart_var.get())
            self._on_reschedule(hour, minute)
            logger.info("Settings saved")
            self._status_var.set("✓ Settings saved.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not save:\n{exc}", parent=self)
            logger.exception("Settings save failed")

    def _run_now(self) -> None:
        self._status_var.set("Running automation…")
        self.update_idletasks()
        threading.Thread(target=self._on_run_now, daemon=True, name="manual-run").start()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


# ── Module-level helper called from app.py ────────────────────────────────────

def show_settings(parent, on_reschedule: Callable, on_run_now: Callable) -> None:
    global _settings_window
    if _settings_window is not None:
        try:
            _settings_window.lift()
            return
        except tk.TclError:
            pass
    _settings_window = SettingsWindow(parent, on_reschedule, on_run_now)
    _settings_window.bind("<Destroy>", lambda _: _clear_ref())


def _clear_ref() -> None:
    global _settings_window
    _settings_window = None
