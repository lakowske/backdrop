"""Core process management functionality for backdrop."""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backdrop.logger import setup_logger, setup_process_logging
from backdrop.utils import (
    daemonize,
    ensure_directories,
    format_memory,
    format_uptime,
    get_process_info,
    is_process_running,
    kill_process_tree,
    sanitize_name,
)

logger = setup_logger("backdrop.process")


class ProcessManager:
    """Manages background processes for backdrop."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        start_verify_delay: float = 0.25,
        restart_delay: float = 0.5,
        log_poll_interval: float = 0.05,
    ) -> None:
        """Initialize the process manager.

        Args:
            base_dir: Base directory for pids and logs (default: current directory)
            start_verify_delay: Delay after starting to verify process (default: 0.25s)
            restart_delay: Delay between stop and start during restart (default: 0.5s)
            log_poll_interval: Polling interval for log following (default: 0.05s)
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.pids_dir, self.logs_dir = ensure_directories(self.base_dir)
        self.start_verify_delay = start_verify_delay
        self.restart_delay = restart_delay
        self.log_poll_interval = log_poll_interval
        logger.info(
            f"ProcessManager initialized - base_dir={self.base_dir}, "
            f"pids_dir={self.pids_dir}, logs_dir={self.logs_dir}, "
            f"start_verify_delay={start_verify_delay}s, "
            f"restart_delay={restart_delay}s, "
            f"log_poll_interval={log_poll_interval}s"
        )

    def start(
        self,
        command: str,
        name: Optional[str] = None,
        cwd: Optional[Path] = None,
    ) -> Optional[int]:
        """Start a process in the background.

        Args:
            command: Shell command to run
            name: Optional process name (default: command name)
            cwd: Optional working directory

        Returns:
            Process ID if successful, None otherwise
        """
        if not command:
            logger.error("No command provided")
            return None

        # Determine process name
        if name is None:
            name = sanitize_name(command)

        logger.info(f"Starting process - name={name}, command={command}")

        # Check if already running
        pid_file = self.pids_dir / f"{name}.pid"
        if pid_file.exists():
            try:
                with open(pid_file, encoding="utf-8") as f:
                    existing_pid = int(f.read().strip())
                if is_process_running(existing_pid):
                    logger.warning(f"Process already running - name={name}, pid={existing_pid}")
                    print(f"✗ {name} is already running (PID: {existing_pid})")
                    return None
                else:
                    logger.info(
                        f"Stale PID file found, removing - name={name}, " f"pid={existing_pid}"
                    )
                    pid_file.unlink()
            except (OSError, ValueError) as e:
                logger.error(f"Error reading PID file - error={e}")
                pid_file.unlink()

        # Set up logging
        stdout_log, stderr_log = setup_process_logging(name, self.logs_dir)

        # Fork to start the process
        pid = os.fork()
        if pid == 0:
            # Child process
            try:
                # Daemonize
                daemonize()

                # Open log files
                with open(stdout_log, "a", encoding="utf-8") as stdout_f, open(
                    stderr_log, "a", encoding="utf-8"
                ) as stderr_f:
                    # Write startup message
                    startup_msg = (
                        f"\n{'='*60}\n"
                        f"Starting {name} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Command: {command}\n"
                        f"{'='*60}\n"
                    )
                    stdout_f.write(startup_msg)
                    stdout_f.flush()

                    # Execute the command
                    proc = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=stdout_f,
                        stderr=stderr_f,
                        cwd=cwd or self.base_dir,
                        preexec_fn=os.setsid,
                    )

                    # Write PID file
                    with open(pid_file, "w", encoding="utf-8") as f:
                        f.write(str(proc.pid))

                    # Child process exits immediately - daemon runs independently

            except Exception as e:
                logger.error(f"Error in child process - error={e}")
                sys.exit(1)
            # Exit child process normally
            sys.exit(0)
        else:
            # Parent process
            # Wait a bit to ensure the process started
            time.sleep(self.start_verify_delay)

            # Read the actual PID from the file
            if pid_file.exists():
                try:
                    with open(pid_file, encoding="utf-8") as f:
                        actual_pid = int(f.read().strip())
                    if is_process_running(actual_pid):
                        logger.info(
                            f"Process started successfully - name={name}, " f"pid={actual_pid}"
                        )
                        print(f"✓ Started {name} (PID: {actual_pid})")
                        print(f"    Logs: {stdout_log}")
                        print(f"    Errors: {stderr_log}")
                        return actual_pid
                except (OSError, ValueError) as e:
                    logger.error(f"Error reading PID file after start - error={e}")

            logger.error(f"Failed to start process - name={name}")
            print(f"✗ Failed to start {name}")
            return None

    def stop(self, name: str, timeout: int = 5) -> bool:
        """Stop a running process.

        Args:
            name: Process name
            timeout: Timeout in seconds for graceful shutdown

        Returns:
            True if process was stopped, False otherwise
        """
        name = sanitize_name(name)
        pid_file = self.pids_dir / f"{name}.pid"

        logger.info(f"Stopping process - name={name}")

        if not pid_file.exists():
            logger.warning(f"PID file not found - name={name}")
            print(f"✗ {name} is not running")
            return False

        try:
            with open(pid_file, encoding="utf-8") as f:
                pid = int(f.read().strip())

            if not is_process_running(pid):
                logger.info(f"Process not running, cleaning up - name={name}, pid={pid}")
                pid_file.unlink()
                print(f"✗ {name} is not running (cleaned up stale PID file)")
                return False

            # Kill the process
            if kill_process_tree(pid, timeout):
                logger.info(f"Process stopped successfully - name={name}, pid={pid}")
                if pid_file.exists():
                    pid_file.unlink()
                print(f"✓ Stopped {name} (PID: {pid})")
                return True
            else:
                logger.error(f"Failed to stop process - name={name}, pid={pid}")
                print(f"✗ Failed to stop {name}")
                return False

        except (OSError, ValueError) as e:
            logger.error(f"Error reading PID file - name={name}, error={e}")
            print(f"✗ Error stopping {name}: {e}")
            return False

    def restart(self, name: str, timeout: int = 5) -> Optional[int]:
        """Restart a process.

        Args:
            name: Process name
            timeout: Timeout for stopping the process

        Returns:
            New process ID if successful, None otherwise
        """
        name = sanitize_name(name)
        logger.info(f"Restarting process - name={name}")

        # Get the original command
        pid_file = self.pids_dir / f"{name}.pid"
        if not pid_file.exists():
            logger.warning(f"Cannot restart, process not running - name={name}")
            print(f"✗ {name} is not running")
            return None

        try:
            with open(pid_file, encoding="utf-8") as f:
                pid = int(f.read().strip())

            # Get process info before stopping
            info = get_process_info(pid)
            if not info:
                logger.error(f"Cannot get process info - name={name}, pid={pid}")
                print(f"✗ Cannot get process info for {name}")
                return None

            command = info["cmdline"]

            # Stop the process
            if self.stop(name, timeout):
                # Wait a bit before restarting
                time.sleep(self.restart_delay)
                # Start it again
                return self.start(command, name)
            else:
                logger.error(f"Failed to stop process for restart - name={name}")
                return None

        except (OSError, ValueError) as e:
            logger.error(f"Error during restart - name={name}, error={e}")
            print(f"✗ Error restarting {name}: {e}")
            return None

    def status(self, verbose: bool = False) -> List[Dict]:
        """Get status of all managed processes.

        Args:
            verbose: Include detailed information

        Returns:
            List of process information dictionaries
        """
        processes = []

        for pid_file in self.pids_dir.glob("*.pid"):
            name = pid_file.stem
            try:
                with open(pid_file, encoding="utf-8") as f:
                    pid = int(f.read().strip())

                info = get_process_info(pid)
                if info:
                    process_data = {
                        "name": name,
                        "pid": pid,
                        "status": "running",
                        "uptime": format_uptime(info["create_time"]),
                    }

                    if verbose:
                        process_data.update(
                            {
                                "cpu_percent": f"{info['cpu_percent']:.1f}%",
                                "memory": format_memory(info["memory_rss"]),
                                "memory_percent": f"{info['memory_percent']:.1f}%",
                                "command": info["cmdline"],
                            }
                        )

                    processes.append(process_data)
                    logger.debug(f"Process status - name={name}, data={process_data}")
                else:
                    # Stale PID file
                    logger.info(f"Removing stale PID file - name={name}, pid={pid}")
                    pid_file.unlink()

            except (OSError, ValueError) as e:
                logger.error(f"Error reading PID file - name={name}, error={e}")
                continue

        return processes

    def stop_all(self, timeout: int = 5) -> int:
        """Stop all running processes.

        Args:
            timeout: Timeout for each process

        Returns:
            Number of processes stopped
        """
        logger.info("Stopping all processes")
        stopped = 0

        for pid_file in self.pids_dir.glob("*.pid"):
            name = pid_file.stem
            if self.stop(name, timeout):
                stopped += 1

        logger.info(f"Stopped {stopped} processes")
        return stopped

    def get_log_files(self, name: str) -> Tuple[Optional[Path], Optional[Path]]:
        """Get log file paths for a process.

        Args:
            name: Process name

        Returns:
            Tuple of (stdout_log, stderr_log) paths
        """
        name = sanitize_name(name)
        stdout_log = self.logs_dir / f"{name}.log"
        stderr_log = self.logs_dir / f"{name}_error.log"

        return (
            stdout_log if stdout_log.exists() else None,
            stderr_log if stderr_log.exists() else None,
        )
