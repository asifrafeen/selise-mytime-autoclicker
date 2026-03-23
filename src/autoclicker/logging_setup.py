"""Configure application-wide logging with rotation."""

import logging
from logging.handlers import RotatingFileHandler

from .config.paths import get_logs_dir


def setup_logging() -> None:
    log_file = get_logs_dir() / "autoclicker.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1 * 1024 * 1024,  # 1 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_log_file_path() -> str:
    return str(get_logs_dir() / "autoclicker.log")
