"""Main application window — always visible on launch.

Shows current configuration, schedule, status, and a Test Run button.
Minimizing sends it to the tray instead of closing.
"""

import logging
import threading
import tkinter as tk
from datetime import datetime
from typing import Callable

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from autoclicker.config.credentials import load_credentials, credentials_exist
from autoclicker.config.settings import load_settings, save_settings
from autoclicker.autostart.autostart import set_autostart
from autoclicker.automation.timesheet import run_timesheet

logger = logging.getLogger(__name__)


class MainWindow(ttk.Window):
    def __init__(self, on_run_now: Callable, on_reschedule: Callable):
        super().__init__(themename="cosmo")
        self.title("MyTime Autoclicker")
        self.resizable(False, False)
        self._on_run_now = on_run_now
        self._on_reschedule = on_reschedule
        self._running = False
        self._last_run: str = "Never"

        self._build_ui()
        self._refresh_config()
        self._center()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Header
        header = ttk.Frame(self, bootstyle="primary")
        header.pack(fill=X)
        ttk.Label(
            header,
            text="  MyTime Autoclicker",
            font=("Segoe UI", 14, "bold"),
            bootstyle="inverse-primary",
        ).pack(side=LEFT, pady=12, padx=4)

        body = ttk.Frame(self, padding=(24, 16))
        body.pack(fill=BOTH, expand=True)

        # ── Account section ───────────────────────────────────────────────
        ttk.Label(body, text="Account", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=W, pady=(0, 6)
        )

        ttk.Label(body, text="Username:", foreground="gray").grid(row=1, column=0, sticky=W, padx=(0, 12), pady=3)
        self._username_var = tk.StringVar()
        ttk.Entry(body, textvariable=self._username_var, width=32).grid(
            row=1, column=1, sticky=EW, pady=3
        )

        ttk.Label(body, text="Password:", foreground="gray").grid(row=2, column=0, sticky=W, padx=(0, 12), pady=3)
        self._password_var = tk.StringVar()
        pw_frame = ttk.Frame(body)
        pw_frame.grid(row=2, column=1, sticky=EW, pady=3)
        self._pw_entry = ttk.Entry(pw_frame, textvariable=self._password_var, show="•", width=26)
        self._pw_entry.pack(side=LEFT)
        self._show_pw_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pw_frame, text="Show", variable=self._show_pw_var,
            bootstyle="round-toggle", command=self._toggle_pw,
        ).pack(side=LEFT, padx=(8, 0))

        self._cred_save_btn = ttk.Button(
            body, text="Save Credentials", bootstyle="primary-outline",
            command=self._save_credentials,
        )
        self._cred_save_btn.grid(row=3, column=1, sticky=W, pady=(4, 0))

        ttk.Separator(body, orient=HORIZONTAL).grid(row=4, column=0, columnspan=2, sticky=EW, pady=12)

        # ── Schedule section ──────────────────────────────────────────────
        ttk.Label(body, text="Schedule", font=("Segoe UI", 10, "bold")).grid(
            row=5, column=0, columnspan=2, sticky=W, pady=(0, 6)
        )
        ttk.Label(body, text="Days:", foreground="gray").grid(row=6, column=0, sticky=W, padx=(0, 12), pady=3)
        ttk.Label(body, text="Mon – Thu  &  Sun", font=("Segoe UI", 9)).grid(row=6, column=1, sticky=W)

        ttk.Label(body, text="Run at:", foreground="gray").grid(row=7, column=0, sticky=W, padx=(0, 12), pady=3)

        time_frame = ttk.Frame(body)
        time_frame.grid(row=7, column=1, sticky=W, pady=3)
        self._hour_var = tk.StringVar()
        self._minute_var = tk.StringVar()
        ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self._hour_var,
                    width=4, format="%02.0f", command=self._save_time).pack(side=LEFT)
        ttk.Label(time_frame, text=" : ").pack(side=LEFT)
        ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self._minute_var,
                    width=4, format="%02.0f", command=self._save_time).pack(side=LEFT)
        ttk.Button(time_frame, text="Apply", bootstyle="primary-outline",
                   command=self._save_time).pack(side=LEFT, padx=(8, 0))

        ttk.Label(body, text="Last run:", foreground="gray").grid(row=8, column=0, sticky=W, padx=(0, 12), pady=3)
        self._last_run_label = ttk.Label(body, text="Never", font=("Segoe UI", 9))
        self._last_run_label.grid(row=8, column=1, sticky=W)

        ttk.Separator(body, orient=HORIZONTAL).grid(row=9, column=0, columnspan=2, sticky=EW, pady=12)

        # ── Autostart toggle ──────────────────────────────────────────────
        self._autostart_var = tk.BooleanVar()
        ttk.Checkbutton(
            body,
            text="Launch at system startup",
            variable=self._autostart_var,
            bootstyle="round-toggle",
            command=self._save_autostart,
        ).grid(row=10, column=0, columnspan=2, sticky=W, pady=(0, 4))

        self._headless_var = tk.BooleanVar()
        ttk.Checkbutton(
            body,
            text="Headless mode — hide browser window (applies to both test & scheduled runs)",
            variable=self._headless_var,
            bootstyle="round-toggle",
            command=self._save_headless,
        ).grid(row=11, column=0, columnspan=2, sticky=W, pady=(0, 12))

        ttk.Separator(body, orient=HORIZONTAL).grid(row=12, column=0, columnspan=2, sticky=EW, pady=(0, 16))

        # ── Status + Test Run ─────────────────────────────────────────────
        status_frame = ttk.Frame(body)
        status_frame.grid(row=13, column=0, columnspan=2, sticky=EW, pady=(0, 10))
        ttk.Label(status_frame, text="Status:", font=("Segoe UI", 9, "bold")).pack(side=LEFT)
        self._status_var = tk.StringVar(value="Idle")
        self._status_label = ttk.Label(
            status_frame, textvariable=self._status_var,
            font=("Segoe UI", 9), bootstyle="success"
        )
        self._status_label.pack(side=LEFT, padx=8)

        self._run_btn = ttk.Button(
            body,
            text="▶  Test Run Now",
            bootstyle="success",
            width=26,
            command=self._trigger_run,
        )
        self._run_btn.grid(row=14, column=0, columnspan=2, ipady=6, pady=(0, 4))

        # Status bar
        self._info_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._info_var, font=("Segoe UI", 8),
                  foreground="gray").pack(side=BOTTOM, anchor=W, padx=16, pady=4)

        body.columnconfigure(1, weight=1)

    # ── Populate from stored config ───────────────────────────────────────────

    def _refresh_config(self) -> None:
        settings = load_settings()
        self._hour_var.set(f"{settings['run_hour']:02d}")
        self._minute_var.set(f"{settings['run_minute']:02d}")
        self._autostart_var.set(settings.get("autostart_enabled", False))
        self._headless_var.set(settings.get("headless", True))

        if credentials_exist():
            try:
                username, password = load_credentials()
                self._username_var.set(username)
                self._password_var.set(password)
            except Exception:
                self._info_var.set("Could not load saved credentials.")
        else:
            self._username_var.set("")
            self._password_var.set("")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _save_time(self) -> None:
        try:
            hour = int(self._hour_var.get())
            minute = int(self._minute_var.get())
        except ValueError:
            return
        settings = load_settings()
        settings["run_hour"] = hour
        settings["run_minute"] = minute
        save_settings(settings)
        self._on_reschedule(hour, minute)
        self._info_var.set(f"Schedule updated to {hour:02d}:{minute:02d}")
        logger.info("Schedule updated to %02d:%02d", hour, minute)

    def _save_autostart(self) -> None:
        settings = load_settings()
        settings["autostart_enabled"] = self._autostart_var.get()
        save_settings(settings)
        set_autostart(self._autostart_var.get())

    def _save_headless(self) -> None:
        settings = load_settings()
        settings["headless"] = self._headless_var.get()
        save_settings(settings)

    def _toggle_pw(self) -> None:
        self._pw_entry.configure(show="" if self._show_pw_var.get() else "•")

    def _save_credentials(self) -> None:
        from autoclicker.config.credentials import save_credentials
        username = self._username_var.get().strip()
        password = self._password_var.get()
        if not username or not password:
            self._info_var.set("Username and password cannot be empty.")
            return
        try:
            save_credentials(username, password)
            self._info_var.set("Credentials saved successfully.")
            logger.info("Credentials updated")
        except Exception as exc:
            self._info_var.set(f"Failed to save credentials: {exc}")
            logger.exception("Credential save failed")

    def _trigger_run(self) -> None:
        if self._running:
            return

        try:
            username, password = load_credentials()
        except FileNotFoundError:
            self._info_var.set("No credentials saved. Complete setup first.")
            return

        # Read headless directly from the live checkbox — not from saved settings
        headless = self._headless_var.get()

        self._running = True
        self._run_btn.configure(state=DISABLED, text="Running…")
        self._status_var.set("Running…")
        self._status_label.configure(bootstyle="warning")
        self._info_var.set(
            f"Running {'headless' if headless else 'with browser visible'}…"
        )

        def _job():
            try:
                # Call run_timesheet directly in this thread so we wait for completion
                run_timesheet(username, password, headless=headless)
                self.after(0, self._on_run_success)
            except Exception as exc:
                self.after(0, lambda: self._on_run_error(str(exc)))

        threading.Thread(target=_job, daemon=True, name="test-run").start()

    def _on_run_success(self) -> None:
        self._running = False
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._last_run = now
        self._last_run_label.configure(text=now)
        self._run_btn.configure(state=NORMAL, text="▶  Test Run Now")
        self._status_var.set("Completed ✓")
        self._status_label.configure(bootstyle="success")
        self._info_var.set("Last run completed successfully.")

    def _on_run_error(self, msg: str) -> None:
        self._running = False
        self._run_btn.configure(state=NORMAL, text="▶  Test Run Now")
        self._status_var.set("Failed ✗")
        self._status_label.configure(bootstyle="danger")
        self._info_var.set(f"Error: {msg[:60]}")

    def _on_close(self) -> None:
        self.withdraw()  # Minimize to tray instead of quitting

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
