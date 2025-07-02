"""Logging configuration and utilities for backdrop."""

import logging
import sys
from pathlib import Path
from typing import Optional, Tuple


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Set up a logger with file and/or console handlers.

    Args:
        name: Logger name
        log_file: Optional path to log file
        level: Logging level (default: INFO)
        format_string: Optional custom format string

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Default format with timestamp, level, file info, and message
    if format_string is None:
        format_string = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if log file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def setup_process_logging(name: str, log_dir: Path) -> Tuple[Path, Path]:
    """Set up logging for a background process.

    Args:
        name: Process name
        log_dir: Directory to store logs

    Returns:
        Tuple of (stdout_log_path, stderr_log_path)
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = log_dir / f"{name}.log"
    stderr_log = log_dir / f"{name}_error.log"

    return stdout_log, stderr_log


def tail_log_file(
    log_file: Path, lines: int = 20, follow: bool = False, poll_interval: float = 0.05
) -> None:
    """Tail a log file, optionally following new lines.

    Args:
        log_file: Path to log file
        lines: Number of lines to show initially (default: 20)
        follow: Whether to follow new lines (default: False)
        poll_interval: Polling interval in seconds for follow mode (default: 0.05s)
    """
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return

    # Read last N lines
    with open(log_file, encoding="utf-8") as f:
        file_lines = f.readlines()
        last_lines = file_lines[-lines:] if len(file_lines) > lines else file_lines

        for line in last_lines:
            print(line.rstrip())

    if follow:
        # Follow mode - watch for new lines
        import time

        try:
            with open(log_file, encoding="utf-8") as f:
                # Go to end of file
                f.seek(0, 2)

                while True:
                    line = f.readline()
                    if line:
                        print(line.rstrip())
                    else:
                        time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\nStopped following log file.")
