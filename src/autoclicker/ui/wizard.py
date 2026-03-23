"""First-run setup wizard using ttkbootstrap.

Collects username, password, run time, and autostart preference,
then saves encrypted credentials and settings.
"""

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from autoclicker.config.credentials import save_credentials
from autoclicker.config.settings import load_settings, save_settings
from autoclicker.autostart.autostart import set_autostart

logger = logging.getLogger(__name__)


class SetupWizard(ttk.Toplevel):
    def __init__(self, parent, on_complete: Callable):
        super().__init__(parent)
        self.title("MyTime Autoclicker — Initial Setup")
        self.resizable(False, False)
        self._on_complete = on_complete

        self._build_ui()
        self._center()
        self.grab_set()  # modal
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 20, "pady": 8}

        # Header
        header = ttk.Frame(self, bootstyle="primary")
        header.pack(fill=X)
        ttk.Label(
            header,
            text="  MyTime Autoclicker Setup",
            font=("Segoe UI", 14, "bold"),
            bootstyle="inverse-primary",
        ).pack(side=LEFT, pady=12)

        # Body frame
        body = ttk.Frame(self, padding=20)
        body.pack(fill=BOTH, expand=True)

        ttk.Label(body, text="Welcome! Please enter your credentials.", font=("Segoe UI", 10)).grid(
            row=0, column=0, columnspan=2, sticky=W, pady=(0, 16)
        )

        # Username
        ttk.Label(body, text="Username (email):").grid(row=1, column=0, sticky=W, **pad)
        self._username_var = tk.StringVar()
        ttk.Entry(body, textvariable=self._username_var, width=34).grid(
            row=1, column=1, sticky=EW, **pad
        )

        # Password
        ttk.Label(body, text="Password:").grid(row=2, column=0, sticky=W, **pad)
        self._password_var = tk.StringVar()
        self._pw_entry = ttk.Entry(body, textvariable=self._password_var, show="•", width=34)
        self._pw_entry.grid(row=2, column=1, sticky=EW, **pad)

        # Show password toggle
        self._show_pw = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            body,
            text="Show password",
            variable=self._show_pw,
            command=self._toggle_pw,
            bootstyle="round-toggle",
        ).grid(row=3, column=1, sticky=W, padx=20)

        # Separator
        ttk.Separator(body).grid(row=4, column=0, columnspan=2, sticky=EW, pady=12)

        # Run time
        ttk.Label(body, text="Run daily at:").grid(row=5, column=0, sticky=W, **pad)
        time_frame = ttk.Frame(body)
        time_frame.grid(row=5, column=1, sticky=W, **pad)

        self._hour_var = tk.StringVar(value="09")
        self._minute_var = tk.StringVar(value="00")
        ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self._hour_var,
                    width=4, format="%02.0f").pack(side=LEFT)
        ttk.Label(time_frame, text=" : ").pack(side=LEFT)
        ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self._minute_var,
                    width=4, format="%02.0f").pack(side=LEFT)
        ttk.Label(time_frame, text="  (Mon–Thu & Sun only)", foreground="gray").pack(side=LEFT)

        # Autostart
        self._autostart_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            body,
            text="Launch automatically at system startup",
            variable=self._autostart_var,
            bootstyle="round-toggle",
        ).grid(row=6, column=0, columnspan=2, sticky=W, padx=20, pady=8)

        # Buttons
        btn_frame = ttk.Frame(body)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(16, 0))
        ttk.Button(btn_frame, text="Save & Start", bootstyle="success",
                   command=self._save).pack(side=RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", bootstyle="secondary",
                   command=self._on_close).pack(side=RIGHT, padx=4)

        body.columnconfigure(1, weight=1)

    # ── Actions ─────────────────────────────────────────────────────────────

    def _toggle_pw(self) -> None:
        self._pw_entry.configure(show="" if self._show_pw.get() else "•")

    def _save(self) -> None:
        username = self._username_var.get().strip()
        password = self._password_var.get()

        if not username or not password:
            messagebox.showerror("Validation Error", "Username and password are required.", parent=self)
            return

        try:
            hour = int(self._hour_var.get())
            minute = int(self._minute_var.get())
        except ValueError:
            messagebox.showerror("Validation Error", "Run time must be numeric.", parent=self)
            return

        try:
            save_credentials(username, password)
            settings = load_settings()
            settings["run_hour"] = hour
            settings["run_minute"] = minute
            settings["autostart_enabled"] = self._autostart_var.get()
            settings["setup_complete"] = True
            save_settings(settings)
            set_autostart(self._autostart_var.get())
            logger.info("Setup wizard completed")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save settings:\n{exc}", parent=self)
            logger.exception("Setup wizard save failed")
            return

        self.destroy()
        self._on_complete()

    def _on_close(self) -> None:
        if messagebox.askyesno(
            "Exit Setup",
            "Setup is not complete. The app will exit.\n\nAre you sure?",
            parent=self,
        ):
            self.master.destroy()

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
