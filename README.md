# Backdrop

Backdrop (bd) is a simple, intuitive server daemon manager. Run any server in the background with automatic logging - no configuration needed.

## Features

- **Dead simple**: Just run `bd start command [args]` and it works
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

### Start a Python server

```bash
bd start app.py
# ✓ Started app (PID: 12345)
#     Logs: ./logs/app.log
#     Error Logs: ./logs/app_error.log
```

### Start a Node.js server

```bash
bd node --name web server.js
# ✓ Started web (PID: 12346)
#     Logs: ./logs/web.log
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
