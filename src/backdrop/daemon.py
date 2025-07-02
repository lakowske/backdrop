"""Core daemon management functionality."""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil


class ServerProcess:
    """Represents a managed server process."""

    def __init__(
        self,
        name: str,
        command: List[str],
        pid: Optional[int] = None,
        started_at: Optional[datetime] = None,
        log_file: Optional[str] = None,
        error_log_file: Optional[str] = None,
        cwd: Optional[str] = None,
    ):
        self.name = name
        self.command = command
        self.pid = pid
        self.started_at = started_at or datetime.now()
        self.log_file = log_file
        self.error_log_file = error_log_file
        self.cwd = cwd or os.getcwd()

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "command": self.command,
            "pid": self.pid,
            "started_at": self.started_at.isoformat(),
            "log_file": self.log_file,
            "error_log_file": self.error_log_file,
            "cwd": self.cwd,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ServerProcess":
        """Create from dictionary."""
        data["started_at"] = datetime.fromisoformat(data["started_at"])
        return cls(**data)

    def is_running(self) -> bool:
        """Check if the process is running."""
        if not self.pid:
            return False
        try:
            process = psutil.Process(self.pid)
            # Verify it's our process by checking command
            cmdline = process.cmdline()
            return len(cmdline) > 0 and any(part in " ".join(cmdline) for part in self.command)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def get_stats(self) -> Optional[Dict]:
        """Get process statistics."""
        if not self.pid or not self.is_running():
            return None
        try:
            process = psutil.Process(self.pid)
            return {
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "uptime": datetime.now() - self.started_at,
                "num_threads": process.num_threads(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None


class DaemonManager:
    """Manages server daemon processes."""

    def __init__(self, state_dir: Optional[Path] = None, log_dir: Optional[Path] = None):
        self.state_dir = state_dir or Path.home() / ".backdrop"
        self.log_dir = log_dir or Path.cwd() / "logs"
        self.state_file = self.state_dir / "servers.json"
        
        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> Dict[str, ServerProcess]:
        """Load server state from disk."""
        if not self.state_file.exists():
            return {}
        
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                return {name: ServerProcess.from_dict(info) for name, info in data.items()}
        except Exception:
            return {}

    def _save_state(self, servers: Dict[str, ServerProcess]) -> None:
        """Save server state to disk."""
        data = {name: server.to_dict() for name, server in servers.items()}
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def _clean_dead_processes(self) -> None:
        """Remove dead processes from state."""
        servers = self._load_state()
        alive_servers = {
            name: server for name, server in servers.items() if server.is_running()
        }
        if len(alive_servers) != len(servers):
            self._save_state(alive_servers)

    def start(
        self,
        command: List[str],
        name: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str]:
        """Start a server process in the background."""
        # Clean up dead processes first
        self._clean_dead_processes()
        
        # Generate name from command if not provided
        if not name:
            base_name = Path(command[0]).stem
            name = base_name
            
        # Check if already running
        servers = self._load_state()
        if name in servers and servers[name].is_running():
            return False, f"Server '{name}' is already running (PID: {servers[name].pid})"
        
        # Set up log files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"{name}.log"
        error_log_file = self.log_dir / f"{name}_error.log"
        
        # Start the process
        try:
            # Prepare environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # Open log files
            with open(log_file, "a") as out_log, open(error_log_file, "a") as err_log:
                # Write startup header
                out_log.write(f"\n{'=' * 60}\n")
                out_log.write(f"Starting {name} at {datetime.now()}\n")
                out_log.write(f"Command: {' '.join(command)}\n")
                out_log.write(f"{'=' * 60}\n\n")
                out_log.flush()
                
                # Start process
                process = subprocess.Popen(
                    command,
                    stdout=out_log,
                    stderr=err_log,
                    cwd=cwd,
                    env=process_env,
                    start_new_session=True,  # Detach from parent
                )
            
            # Create server record
            server = ServerProcess(
                name=name,
                command=command,
                pid=process.pid,
                started_at=datetime.now(),
                log_file=str(log_file),
                error_log_file=str(error_log_file),
                cwd=cwd or os.getcwd(),
            )
            
            # Save state
            servers[name] = server
            self._save_state(servers)
            
            # Give it a moment to start
            time.sleep(0.5)
            
            # Verify it's running
            if not server.is_running():
                del servers[name]
                self._save_state(servers)
                return False, f"Process started but immediately exited. Check {error_log_file}"
            
            return True, f"Started {name} (PID: {process.pid})"
            
        except Exception as e:
            return False, f"Failed to start server: {str(e)}"

    def stop(self, name: str, force: bool = False) -> Tuple[bool, str]:
        """Stop a server process."""
        servers = self._load_state()
        
        if name not in servers:
            return False, f"Server '{name}' not found"
        
        server = servers[name]
        if not server.is_running():
            del servers[name]
            self._save_state(servers)
            return True, f"Server '{name}' is not running (cleaned up state)"
        
        try:
            process = psutil.Process(server.pid)
            
            # Try graceful shutdown first
            if not force:
                process.terminate()
                
                # Wait up to 10 seconds for graceful shutdown
                for _ in range(10):
                    if not server.is_running():
                        break
                    time.sleep(1)
            
            # Force kill if still running
            if server.is_running():
                process.kill()
                time.sleep(0.5)
            
            # Remove from state
            del servers[name]
            self._save_state(servers)
            
            return True, f"Stopped {name}"
            
        except Exception as e:
            return False, f"Failed to stop server: {str(e)}"

    def restart(self, name: str) -> Tuple[bool, str]:
        """Restart a server process."""
        servers = self._load_state()
        
        if name not in servers:
            return False, f"Server '{name}' not found"
        
        server = servers[name]
        
        # Stop the server
        stop_success, stop_msg = self.stop(name)
        if not stop_success and "not running" not in stop_msg:
            return False, f"Failed to stop server: {stop_msg}"
        
        # Wait a moment
        time.sleep(1)
        
        # Start it again with the same command
        return self.start(
            command=server.command,
            name=name,
            cwd=server.cwd,
        )

    def list_servers(self) -> List[ServerProcess]:
        """List all managed servers."""
        self._clean_dead_processes()
        servers = self._load_state()
        return list(servers.values())

    def get_server(self, name: str) -> Optional[ServerProcess]:
        """Get a specific server by name."""
        servers = self._load_state()
        return servers.get(name)

    def stop_all(self) -> List[Tuple[str, bool, str]]:
        """Stop all running servers."""
        results = []
        servers = self._load_state()
        
        for name in list(servers.keys()):
            success, msg = self.stop(name)
            results.append((name, success, msg))
        
        return results