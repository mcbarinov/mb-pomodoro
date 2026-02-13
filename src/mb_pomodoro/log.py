"""Logging configuration for mb-pomodoro."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_path: Path) -> None:
    """Configure package logger with a rotating file handler.

    Idempotent — skips if handler is already attached.
    """
    root = logging.getLogger("mb_pomodoro")
    if root.handlers:
        return

    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))

    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
