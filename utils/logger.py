"""
Logging configuration for LocalStudy.
Handles console logging and rotating file logs with standard formatting.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "localstudy", log_dir: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a singleton-style logger for the application."""
    # Ensure Windows console handles arbitrary unicode titles without crashing
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # File handler
    if log_dir is None:
        log_dir = Path.home() / ".localstudy" / "logs"
    
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / "localstudy.log"
        file_handler = RotatingFileHandler(
            file_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not configure file logging in {log_dir}: {e}", file=sys.stderr)

    return logger


logger = setup_logger()
