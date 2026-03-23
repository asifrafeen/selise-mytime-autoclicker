# CLAUDE.md — MyTime Autoclicker

This file gives Claude full context to resume work on this project in a new session.

---

## What This Project Is

A cross-platform desktop automation app that logs into `https://mytime.selise.biz`, creates today's timesheet, fills in **9 hours** under the **General Admin** column, and saves — automatically every working day (Mon–Thu & Sun), at a user-configured time.

Built for **Asif Rafeen** (`asif.rafeen@selisegroup.com`), a developer at Selise Group. The app automates his daily timesheet submission.

---

## Repository

- **GitHub**: `git@github-work:asifrafeen/selise-mytime-autoclicker.git`
- **SSH alias**: `github-work` → uses `~/.ssh/id_ed25519_github_work` (work account: `asifrafeen`)
- **Personal SSH alias**: `github-personal` → uses `~/.ssh/id_ed25519_github_personal` (personal account: `raf1305`)
- **Branch**: `master`

---

## Tech Stack

| Purpose | Library |
|---|---|
| Browser automation | `playwright` (Chromium) |
| GUI | `ttkbootstrap` (tkinter wrapper, theme: `cosmo`) |
| System tray | `pystray` + `Pillow` |
| Scheduler | `APScheduler 3.x` (`BackgroundScheduler` + `CronTrigger`) |
| Encryption | `cryptography` (Fernet / PBKDF2-HMAC-SHA256) |
| Packaging | `pyinstaller` (dev dependency) |
| Package manager | `uv` |

---

## Project Structure

```
selise-mytime-autoclicker/
├── src/
│   └── autoclicker/
│       ├── main.py                  # Entry point, single-instance IPC, signal handling
│       ├── logging_setup.py         # RotatingFileHandler logger
│       ├── automation/
│       │   └── timesheet.py         # Full Playwright automation flow
│       ├── config/
│       │   ├── credentials.py       # Fernet encrypt/decrypt
│       │   ├── settings.py          # settings.json read/write
│       │   └── paths.py             # Platform-aware appdata dir
│       ├── scheduler/
│       │   └── scheduler.py         # APScheduler, Mon–Thu & Sun only
│       ├── autostart/
│       │   └── autostart.py         # Startup entry per OS
│       ├── tray/
│       │   └── tray_icon.py         # pystray tray icon
│       └── ui/
│           ├── app.py               # Bootstrap — wires all modules
│           ├── main_window.py       # Main window (always visible on launch)
│           └── wizard.py            # First-run setup wizard
├── mytime.py                        # Original standalone script (kept for reference, credentials scrubbed)
├── main.py                          # Original hr.selise.biz script (kept for reference, credentials scrubbed)
├── pyproject.toml
├── README.md
└── CLAUDE.md                        # This file
```

---

## How to Run

```bash
# Clone and install
git clone git@github-work:asifrafeen/selise-mytime-autoclicker.git
cd selise-mytime-autoclicker
uv sync
uv run playwright install chromium

# Run
uv run mytime

# Run detached from terminal (recommended)
uv run mytime &

# Bring window back when hidden
uv run mytime   # signals running instance via IPC socket
```

---

## Key Design Decisions Made in This Session

### 1. Single-instance + IPC via local TCP socket (port 47381)
- Replaced lock files (`fcntl`/`msvcrt`) and `SIGUSR1` signals — neither works cross-platform
- First launch binds port 47381 → becomes primary instance
- Second launch fails to bind → connects, sends `b"SHOW"`, exits
- Primary instance polls every 250ms for the SHOW flag and calls `deiconify()`
- Advantage: OS releases the port immediately on crash — no stale locks ever

### 2. Fernet encryption for credentials
- Key derived via PBKDF2-HMAC-SHA256 (480,000 iterations) from `uuid.getnode()` (MAC address)
- Machine-specific: `credentials.enc` cannot be decrypted on another machine
- Stored in platform appdata dir (see below)

### 3. Appdata paths per OS
- **Linux**: `~/.config/MyTimeAutoclicker/`
- **Windows**: `%APPDATA%\MyTimeAutoclicker\`
- **macOS**: `~/Library/Application Support/MyTimeAutoclicker/`
- Files: `settings.json`, `credentials.enc`, `logs/autoclicker.log`

### 4. Dynamic column detection in Playwright
- The timesheet table uses Vue.js with auto-generated `__BVID__` IDs that change every session
- Fix: scan `<th>` text for `"General Admin"` at runtime → get column index → build `nth-child` CSS selector
- `page.locator().fill("9")` is used (not `page.evaluate`) to properly trigger Vue reactivity

### 5. Thread model
- Main thread: tkinter event loop (only thread allowed to touch the GUI)
- `tray-thread`: pystray daemon thread
- APScheduler pool: fires the daily job
- `playwright-job`: spawned per run, `browser.close()` always in `finally`
- Background → GUI communication: `root.after(0, callback)` only — never direct tk calls

### 6. Autostart per OS
- **Linux**: writes `~/.config/autostart/MyTimeAutoclicker.desktop`
- **Windows**: writes to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- **macOS**: writes `~/Library/LaunchAgents/com.mytimeautoclicker.plist`

### 7. SIGTSTP/SIGCONT (Ctrl+Z handling) — Unix only
- Guarded with `hasattr(signal, "SIGTSTP")` so Windows doesn't crash
- Ctrl+Z hides the window cleanly; `fg` restores it

---

## UI Overview

The **main window** is always shown on launch (not hidden in tray by default). It contains:
- **Account section**: editable username + password fields (password hidden by default, Show toggle to reveal), Save Credentials button
- **Schedule section**: day label (Mon–Thu & Sun), HH:MM spinbox + Apply button, Last run timestamp
- **Options**: Launch at startup toggle, Headless mode toggle (applies to both test & scheduled runs)
- **Test Run Now** button: runs the automation immediately in a background thread, using the live headless checkbox value (not saved settings)
- Status label + bottom status bar for feedback messages

Closing the window hides it (withdraw); running `uv run mytime` again brings it back.

---

## Automation Flow (`automation/timesheet.py`)

1. `page.goto("https://mytime.selise.biz/")`
2. Fill `input[name='email']` and `input[name='password']`
3. Wait for submit button to be enabled (Angular/Vue disables it until form is valid), click it
4. `page.wait_for_load_state("networkidle")`
5. Click `button:has-text('Create Timesheet for Today')`
6. `page.wait_for_load_state("networkidle")`
7. Click `button:has-text('Edit')`
8. Wait for `table[data-test-id='table-record-list'] tbody tr`
9. Evaluate JS to find column index of `"General Admin"` header
10. `page.locator(f"...td:nth-child({col_index + 1}) input[type='number']").fill("9")`
11. Click `button[data-test-id='button-save']`
12. `page.wait_for_timeout(2000)` then `browser.close()`

A `threading.Event` (`_cancel_event`) allows mid-run cancellation.

---

## Known Issues / Limitations

- **Linux system tray not visible by default on GNOME**: requires `gnome-shell-extension-appindicator`. Without it, use terminal to bring window back.
- **Windows bring-forward via IPC**: works via socket (port 47381). If port is in use by another app, the single-instance check will incorrectly think another instance is running — unlikely but possible.
- **Fernet key is machine-specific**: credentials must be re-entered after moving to a new machine.
- **headless=True is the default**: user must uncheck "Headless mode" in the GUI to watch the browser run.
- **No missed-run recovery**: if the PC is off at the scheduled time, the job is skipped for that day.

---

## What Was Worked On in This Session (Chronological)

1. Fixed login selectors in original `mytime.py` — email field has no `type="email"`, only `name="email"`
2. Fixed timesheet table filling — dynamic `__BVID__` IDs replaced with column-index approach
3. Fixed `Illegal invocation` JS error — replaced `evaluate()` native setter hack with `locator().fill()`
4. Designed full app architecture (planning phase)
5. Implemented full app: wizard, main window, tray, scheduler, credentials, autostart, logging, IPC
6. Added `pyproject.toml` entry point so `uv run mytime` works
7. Fixed `ModuleNotFoundError` — added `src` to `sys.path` for direct `python main.py` execution
8. Redesigned UI to always show main window (not hidden at start)
9. Added credential editing (username + password fields) to main window with Show/Hide toggle
10. Added headless mode toggle in UI — wired directly to live checkbox value, not saved settings
11. Fixed double-threading bug in test run — single thread calls `run_timesheet` directly
12. Replaced lock file + SIGUSR1 signal approach with cross-platform TCP socket IPC
13. Fixed `SIGTSTP`/`SIGCONT` Windows crash — guarded with `hasattr`
14. Fixed stale lock file empty-PID bug (now moot, lock file removed)
15. Fixed `_acquire_lock` truncation bug — used `a+` mode (now moot, lock file removed)
16. Wrote README.md with project summary + full technical overview
17. Confirmed cross-platform compatibility: Windows ✅, macOS ✅, Linux ✅ — single codebase

---

## What Might Still Need Work

- **PyInstaller build**: `build.spec` file not yet written; Playwright browser bundling not configured
- **Windows bring-forward**: IPC socket works but no fallback if port 47381 is taken
- **Missed run recovery**: optionally run immediately on startup if today's scheduled time was missed
- **Notification on completion**: desktop toast notification after successful submission
- **"Create Timesheet for Today" button may not appear**: if timesheet already exists for today, the site shows a different button — the automation will fail silently; needs handling
- **Testing**: no automated tests written yet
