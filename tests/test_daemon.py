"""Basic tests for daemon functionality."""

import os
import sys
import time
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backdrop.daemon import DaemonManager, ServerProcess


def test_server_process_creation():
    """Test creating a ServerProcess object."""
    server = ServerProcess(
        name="test_server",
        command=["python", "test.py"],
        pid=12345,
    )
    
    assert server.name == "test_server"
    assert server.command == ["python", "test.py"]
    assert server.pid == 12345
    assert server.started_at is not None


def test_server_process_serialization():
    """Test converting ServerProcess to/from dict."""
    server = ServerProcess(
        name="test_server",
        command=["python", "test.py"],
        pid=12345,
    )
    
    # Convert to dict
    data = server.to_dict()
    assert data["name"] == "test_server"
    assert data["command"] == ["python", "test.py"]
    assert data["pid"] == 12345
    assert "started_at" in data
    
    # Convert back from dict
    server2 = ServerProcess.from_dict(data)
    assert server2.name == server.name
    assert server2.command == server.command
    assert server2.pid == server.pid


def test_daemon_manager_initialization(tmp_path):
    """Test DaemonManager initialization."""
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "logs"
    
    manager = DaemonManager(state_dir=state_dir, log_dir=log_dir)
    
    assert manager.state_dir == state_dir
    assert manager.log_dir == log_dir
    assert state_dir.exists()
    assert log_dir.exists()


def test_start_simple_server(tmp_path):
    """Test starting a simple server process."""
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "logs"
    
    manager = DaemonManager(state_dir=state_dir, log_dir=log_dir)
    
    # Create a simple test script
    test_script = tmp_path / "test_server.py"
    test_script.write_text("""
import time
import sys

print("Server started", flush=True)
sys.stdout.flush()

# Run for a short time
time.sleep(2)
print("Server stopping", flush=True)
""")
    
    # Start the server
    success, message = manager.start(
        command=[sys.executable, str(test_script)],
        name="test_server"
    )
    
    assert success
    assert "Started test_server" in message
    
    # Check that the server is in the list
    servers = manager.list_servers()
    assert len(servers) == 1
    assert servers[0].name == "test_server"
    
    # Stop the server
    success, message = manager.stop("test_server")
    assert success
    
    # Verify it's stopped
    servers = manager.list_servers()
    assert len(servers) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])