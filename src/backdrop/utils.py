"""Utility functions for backdrop."""

import contextlib
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import psutil


def format_uptime(start_time: float) -> str:
    """Format process uptime in human-readable format.

    Args:
        start_time: Process start time as Unix timestamp

    Returns:
        Formatted uptime string (e.g., "5m 32s", "2h 15m")
    """
    uptime_seconds = int(time.time() - start_time)

    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts[:2])  # Show at most 2 units


def format_memory(bytes_value: int) -> str:
    """Format memory size in human-readable format.

    Args:
        bytes_value: Memory size in bytes

    Returns:
        Formatted memory string (e.g., "125.5 MB")
    """
    value = float(bytes_value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


def get_process_info(pid: int) -> Optional[dict]:
    """Get detailed information about a process.

    Args:
        pid: Process ID

    Returns:
        Dictionary with process information, or None if process not found
    """
    try:
        proc = psutil.Process(pid)

        # Get process info with proper error handling
        info = {
            "pid": pid,
            "name": proc.name(),
            "status": proc.status(),
            "create_time": proc.create_time(),
            "cmdline": " ".join(proc.cmdline()),
        }

        # Try to get CPU and memory info
        try:
            info["cpu_percent"] = proc.cpu_percent(interval=0.1)
            memory_info = proc.memory_info()
            info["memory_rss"] = memory_info.rss
            info["memory_percent"] = proc.memory_percent()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            info["cpu_percent"] = 0.0
            info["memory_rss"] = 0
            info["memory_percent"] = 0.0

        return info

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running.

    Args:
        pid: Process ID

    Returns:
        True if process is running, False otherwise
    """
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def kill_process_tree(pid: int, timeout: int = 5) -> bool:
    """Kill a process and all its children.

    Args:
        pid: Process ID
        timeout: Timeout in seconds for graceful shutdown

    Returns:
        True if process was killed successfully, False otherwise
    """
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)

        # Send SIGTERM to parent and children
        for child in children:
            with contextlib.suppress(psutil.NoSuchProcess):
                child.terminate()

        parent.terminate()

        # Wait for processes to terminate
        gone, alive = psutil.wait_procs([*children, parent], timeout=timeout, callback=None)

        # Force kill any remaining processes
        for proc in alive:
            with contextlib.suppress(psutil.NoSuchProcess):
                proc.kill()

        return True

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def sanitize_name(name: str) -> str:
    """Sanitize a process name for use in filenames.

    Args:
        name: Process name or shell command

    Returns:
        Sanitized name safe for filenames
    """
    # Extract meaningful command name from shell command
    if " " in name:
        # Handle environment variables (e.g., "PYTHONPATH=/opt python server.py")
        parts = name.split()
        for part in parts:
            if "=" not in part and not part.startswith("-"):
                name = part
                break
        else:
            # Fallback to first part if no clean command found
            name = parts[0]
    
    # Extract basename if it's a path
    name = os.path.basename(name)
    
    # Remove file extension if present
    if name.endswith((".py", ".js", ".rb", ".sh")):
        name = Path(name).stem

    # Replace unsafe characters
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return "".join(c if c in safe_chars else "_" for c in name)


def ensure_directories(base_dir: Path) -> Tuple[Path, Path]:
    """Ensure required directories exist.

    Args:
        base_dir: Base directory for backdrop data

    Returns:
        Tuple of (pids_dir, logs_dir)
    """
    pids_dir = base_dir / "pids"
    logs_dir = base_dir / "logs"

    pids_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    return pids_dir, logs_dir


def daemonize() -> None:
    """Daemonize the current process.

    This performs a double fork to properly detach from the terminal.
    """
    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process exits
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"First fork failed: {e}\n")
        sys.exit(1)

    # Decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process exits
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"Second fork failed: {e}\n")
        sys.exit(1)

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    # Close file descriptors
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, sys.stdin.fileno())
    os.close(devnull)
