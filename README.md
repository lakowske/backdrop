# Backdrop

A simple, intuitive server daemon manager. Run any server in the background with automatic logging - no configuration needed.

## Features

- **Dead simple**: Just run `bd my_server.py` and it works
- **Automatic logging**: Logs are automatically saved to `./logs/`
- **Multiple servers**: Manage multiple server processes from one tool
- **Smart defaults**: Automatically detects Python scripts, creates log directories
- **Process monitoring**: View CPU, memory usage, and uptime
- **Graceful shutdown**: Proper signal handling for clean stops

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Start a server in the background
bd my_server.py

# Start with custom name
bd my_server.py --name api

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
bd app.py
# ✓ Started app (PID: 12345)
#     Logs: ./logs/app.log
```

### Start a Node.js server
```bash
bd node server.js --name web
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
bd my_server.py --cwd /path/to/project
```

### View detailed status
```bash
bd status --verbose
# Shows CPU %, memory usage, and full command
```

### View error logs
```bash
bd logs my_server --error
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
3. Tracking PIDs in `~/.backdrop/servers.json`
4. Monitoring process health using psutil
5. Handling graceful shutdowns with configurable timeouts

## License

MIT