"""Application entry point.

Sets up Playwright browser path for frozen (PyInstaller) builds,
initialises logging, then hands control to the UI layer.
"""

import os
import sys

# ── Frozen-app browser path fix (must run before any playwright import) ──────
if getattr(sys, "frozen", False):
    _browsers_path = os.path.join(os.path.dirname(sys.executable), "_playwright_browsers")
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", _browsers_path)

from autoclicker.logging_setup import setup_logging  # noqa: E402
from autoclicker.ui.app import create_root, bootstrap  # noqa: E402


def main() -> None:
    setup_logging()

    root = create_root()
    bootstrap(root)
    root.mainloop()


if __name__ == "__main__":
    main()
