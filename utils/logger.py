"""Structured console logger shared across the pipeline."""
from __future__ import annotations

import logging
import sys

_FMT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
_DATE = "%H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATE))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
