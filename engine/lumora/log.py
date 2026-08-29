"""Plain-English logging: every message shows on screen AND is saved to engine/logs/."""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = _LOG_DIR / f"lumora_{time.strftime('%Y-%m-%d')}.log"

    logger = logging.getLogger("lumora")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    to_file = logging.FileHandler(logfile, encoding="utf-8")
    to_file.setFormatter(fmt)
    logger.addHandler(to_file)

    logger.propagate = False
    _logger = logger
    return logger
