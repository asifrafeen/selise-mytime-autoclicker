# PyInstaller spec for MyTime Autoclicker
# Build: pyinstaller build.spec
# Must be built on the TARGET platform (Windows for .exe, Linux for ELF).

import os
import sys
from pathlib import Path

# Locate the Playwright driver directory
from playwright._impl._driver import compute_driver_executable
playwright_driver_dir = str(Path(compute_driver_executable()[0]).parent)

block_cipher = None

a = Analysis(
    ["src/autoclicker/main.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        # Playwright Node.js IPC driver
        (playwright_driver_dir, "playwright/driver"),
        # App icon
        ("assets", "assets"),
    ],
    hiddenimports=[
        "playwright",
        "playwright.sync_api",
        "playwright._impl._driver",
        "playwright._impl._sync_base",
        "greenlet",
        "pyee",
        "pyee.base",
        "pyee.asyncio",
        "pystray",
        "pystray._base",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "ttkbootstrap",
        "ttkbootstrap.themes",
        "apscheduler",
        "apscheduler.schedulers.background",
        "apscheduler.triggers.cron",
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat.primitives.hashes",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MyTimeAutoclicker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # DO NOT enable — corrupts the Playwright Node.js binary
    console=False,      # No terminal window on Windows
    icon=None,          # Replace with "assets/icon.ico" if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MyTimeAutoclicker",
)
