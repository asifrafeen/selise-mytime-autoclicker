# MyTime Autoclicker

A desktop automation tool that logs into [mytime.selise.biz](https://mytime.selise.biz), creates today's timesheet, fills in 9 hours under the **General Admin** column, and saves — automatically, every working day.

---

## What It Does

Manually submitting a daily timesheet is a repetitive task. This app automates the full flow:

1. Opens a Chromium browser (visible or headless)
2. Logs in with your credentials
3. Clicks **Create Timesheet for Today**
4. Clicks **Edit**
5. Finds the **General Admin** column dynamically and fills it with `9`
6. Clicks **Save**

It runs once a day at a configured time, Monday–Thursday and Sunday, skipping Friday and Saturday. Everything is configurable from a GUI — no editing files manually.

---

## Features

- **Always-on GUI** — window shows on every launch with current config
- **Secure credential storage** — username and password are encrypted using Fernet (AES-128) with a machine-specific key; credentials cannot be copied to another machine
- **Show/hide password** — password field is masked by default with a toggle to reveal
- **Configurable schedule** — set the run time via spinbox, applied immediately
- **Headless toggle** — run the browser silently in the background or watch it work
- **Test Run button** — trigger the automation manually at any time
- **Autostart** — optionally launch at system startup (cross-platform)
- **System tray** — minimizing sends it to the tray; re-running brings the window back
- **Single instance** — launching a second time brings the existing window forward instead of opening a duplicate
- **Rotating logs** — execution history stored locally, viewable from the tray menu

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Playwright browsers: `uv run playwright install chromium`

### Linux (GNOME) — system tray visibility

GNOME does not show tray icons by default. Install the AppIndicator extension to see the tray icon:

```bash
sudo apt install gnome-shell-extension-appindicator
gnome-extensions enable ubuntu-appindicators@ubuntu.com
# Then log out and back in
```

Without it, use `uv run mytime` from a terminal to bring the window back.

---

## Installation

```bash
git clone git@github-work:asifrafeen/selise-mytime-autoclicker.git
cd selise-mytime-autoclicker
uv sync
uv run playwright install chromium
```

---

## Usage

```bash
uv run mytime
```

On first launch, a setup wizard will prompt for your username, password, and preferred run time. These are encrypted and stored locally.

To run in the background (recommended — detaches from terminal):

```bash
uv run mytime &
```

To bring the window back when it's hidden:

```bash
uv run mytime   # signals the running instance to show its window
```

---

## Project Structure

```
selise-mytime-autoclicker/
├── src/
│   └── autoclicker/
│       ├── main.py                  # Entry point, single-instance lock, signal handling
│       ├── logging_setup.py         # Rotating file logger
│       ├── automation/
│       │   └── timesheet.py         # Playwright automation flow
│       ├── config/
│       │   ├── credentials.py       # Fernet encryption / decryption
│       │   ├── settings.py          # Read/write settings.json
│       │   └── paths.py             # Platform-aware appdata directory
│       ├── scheduler/
│       │   └── scheduler.py         # APScheduler — daily cron, day-of-week filter
│       ├── autostart/
│       │   └── autostart.py         # Startup entry (registry / .desktop / plist)
│       ├── tray/
│       │   └── tray_icon.py         # pystray system tray icon
│       └── ui/
│           ├── app.py               # Bootstrap — wires all modules together
│           ├── main_window.py       # Main window (always visible)
│           └── wizard.py            # First-run setup wizard
├── mytime.py                        # Original standalone script (kept for reference)
├── pyproject.toml
└── README.md
```

---

## Technical Overview

### Automation Engine

`automation/timesheet.py` drives Playwright's synchronous API against `mytime.selise.biz`. Key design decisions:

- **Dynamic column detection** — the table uses Vue.js with auto-generated `__BVID__` IDs that change every session. The script resolves the correct input by scanning `<th>` text content for `"General Admin"` at runtime, then constructs a stable `nth-child` CSS selector.
- **Cancellation** — a `threading.Event` allows the job to be aborted cleanly between steps without leaving an orphaned browser process (`browser.close()` is always called in a `finally` block).
- **Headless flag** — passed explicitly at call time so the live UI checkbox value is always used, never a stale cached setting.

### Credential Security

`config/credentials.py` uses **Fernet symmetric encryption** from the `cryptography` library:

- The encryption key is derived via **PBKDF2-HMAC-SHA256** (480,000 iterations) from the machine's MAC address + a static passphrase
- This makes the encrypted file machine-specific — copying `credentials.enc` to another machine produces an unreadable blob
- Credentials are decrypted only at runtime, immediately before the Playwright job starts

> **Note:** This protects against casual inspection of the appdata folder. It does not protect against a determined attacker with full access to the machine.

### Scheduler

`scheduler/scheduler.py` uses **APScheduler 3.x** with a `BackgroundScheduler` and `CronTrigger`. The day-of-week filter (`mon-thu,sun`) is declared at startup and updated live when the user changes the run time via the GUI — no restart needed.

### Thread Model

The app uses four distinct threads:

| Thread | Purpose |
|---|---|
| Main thread | tkinter event loop — all GUI updates |
| `tray-thread` | pystray icon event loop (daemon) |
| APScheduler pool | Fires the scheduled job |
| `playwright-job` | Runs the Playwright automation (spawned per run) |

Background threads never call tkinter directly. They use `root.after(0, callback)` to post work back to the main thread safely.

### Single Instance

`main.py` uses `fcntl.flock` (Linux/macOS) or `msvcrt.locking` (Windows) on a lock file in the appdata directory. The lock file stores the running process's PID. A second invocation reads the PID and sends `SIGUSR1` to the first process, which responds by bringing its window to the front. The signal handler sets a flag; a 250ms polling loop on the tkinter event thread checks it and calls `deiconify()`.

### Autostart

`autostart/autostart.py` writes the appropriate startup entry per platform:

- **Windows** — `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` registry key
- **Linux** — `~/.config/autostart/MyTimeAutoclicker.desktop`
- **macOS** — `~/Library/LaunchAgents/com.mytimeautoclicker.plist`

### Data Storage

All app data is stored in a platform-appropriate directory resolved by `config/paths.py`:

| Platform | Path |
|---|---|
| Linux | `~/.local/share/MyTimeAutoclicker/` |
| Windows | `%APPDATA%\MyTimeAutoclicker\` |
| macOS | `~/Library/Application Support/MyTimeAutoclicker/` |

Files stored: `settings.json`, `credentials.enc`, `app.lock`, `logs/autoclicker.log`

---

## Dependencies

| Package | Purpose |
|---|---|
| `playwright` | Browser automation |
| `ttkbootstrap` | Modern tkinter UI theme |
| `pystray` + `Pillow` | System tray icon |
| `APScheduler` | Daily job scheduler |
| `cryptography` | Fernet credential encryption |

Dev: `pyinstaller` (for building a standalone executable)

---

## Building an Executable

```bash
uv run pyinstaller build.spec
```

> Playwright browser binaries are not bundled. On first run of the built `.exe`, the app will download Chromium automatically.
