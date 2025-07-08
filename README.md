# Backdrop

Backdrop (bd) is a simple, intuitive server daemon manager. Run any server in the background with automatic logging - no configuration needed.

## Features

- **Dead simple**: Just run `bd start command [args]` and it works
- **Shell command support**: Run complex shell commands with pipes, redirections, and environment variables
- **Automatic logging**: Stdout and Stderr logs are automatically saved to `./logs/command.log` and `./logs/command_error.log`
- **Multiple servers**: Manage multiple server processes using .pid files from one tool
- **Process monitoring**: View CPU, memory usage, and uptime
- **Graceful shutdown**: Proper signal handling for clean stops

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Start a server in the background
bd start my_server.py

# Start with custom name
bd start --name api my_server.py

# Check status of all servers
bd status

# View logs
bd logs my_server

# Stop a server
bd stop my_server

# Restart a server
bd restart my_server
```

## Usage Examples

### Simple Commands

```bash
# Start a simple command
bd start sleep 30
# ✓ Started sleep (PID: 12345)

# Start a Python server
bd start python app.py
# ✓ Started python (PID: 12346)
```

### Complex Shell Commands

For commands with options that might conflict with backdrop's options, use `--` to separate:

```bash
# Start Python HTTP server
bd start -- python -m http.server 8001
# ✓ Started python (PID: 12347)

# Start uvicorn with options
bd start -- uvicorn app:main --host 0.0.0.0 --port 8000
# ✓ Started uvicorn (PID: 12348)

# Commands with environment variables
bd start -- PYTHONPATH=/tmp python server.py
# ✓ Started python (PID: 12349)
```

### Using Quotes (Alternative)

```bash
# You can also use quotes to wrap the entire command
bd start "uvicorn app:main --host 0.0.0.0 --port 8000"
# ✓ Started uvicorn (PID: 12350)
```

### Custom Process Names

```bash
# Use --name to specify a custom process name
bd start --name api -- uvicorn app:main --host 0.0.0.0 --port 8000
# ✓ Started api (PID: 12351)
```

### View all running servers

```bash
bd status
# ┏━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━┳━━━━━━━━┓
# ┃ Name    ┃ Status    ┃  PID ┃ Uptime ┃
# ┡━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━╇━━━━━━━━┩
# │ app     │ ● Running │ 12345│ 5m 32s │
# │ web     │ ● Running │ 12346│ 2m 15s │
# └─────────┴───────────┴──────┴────────┘
```

### Follow logs in real-time

```bash
bd logs app --follow
```

### Stop all servers

```bash
bd stop-all
```

## Advanced Usage

### Custom working directory

```bash
bd --cwd /path/to/project my_server.py
```

### View detailed status

```bash
bd status --verbose
# Shows CPU %, memory usage, and full command
```

### View error logs

```bash
bd logs --error my_server
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run formatter
black src/

# Run linter
ruff check src/

# Run type checker
mypy src/
```

## How It Works

Backdrop manages server processes by:

1. Starting processes in the background with proper daemonization
2. Redirecting stdout/stderr to timestamped log files
3. Tracking PIDs in `./pids/command.pid`
4. Monitoring process health using psutil
5. Handling graceful shutdowns with configurable timeouts

## License

MIT
