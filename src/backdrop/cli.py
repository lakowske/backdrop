"""CLI interface for backdrop."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from backdrop.daemon import DaemonManager


console = Console()


def get_manager() -> DaemonManager:
    """Get the daemon manager instance."""
    return DaemonManager()


def format_uptime(delta) -> str:
    """Format timedelta to human readable string."""
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--version", is_flag=True, help="Show version")
def cli(ctx: click.Context, version: bool) -> None:
    """Backdrop (bd) - Simple server daemon manager.
    
    Run any server in the background with automatic logging.
    
    Examples:
        bd my_server.py              # Start server
        bd stop my_server            # Stop server
        bd status                    # Show all servers
        bd logs my_server            # View logs
    """
    if version:
        from backdrop import __version__
        console.print(f"backdrop version {__version__}")
        ctx.exit()
    
    # If no command provided but arguments given, assume it's a start command
    if ctx.invoked_subcommand is None and len(sys.argv) > 1:
        # Check if it's a file path
        potential_file = sys.argv[1]
        if os.path.exists(potential_file) or "." in potential_file:
            # Redirect to start command
            ctx.invoke(start, command=sys.argv[1:])
        else:
            # Show help
            console.print(ctx.get_help())


@cli.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--name", "-n", help="Custom name for the server")
@click.option("--cwd", help="Working directory for the server")
def start(command: tuple, name: Optional[str], cwd: Optional[str]) -> None:
    """Start a server in the background."""
    command_list = list(command)
    
    # If first arg is a Python file, prepend python interpreter
    if command_list[0].endswith(".py"):
        command_list.insert(0, sys.executable)
    
    manager = get_manager()
    success, message = manager.start(command_list, name=name, cwd=cwd)
    
    if success:
        console.print(f"[green]✓[/green] {message}")
        server = manager.get_server(name or Path(command[0]).stem)
        if server:
            console.print(f"    Logs: {server.log_file}")
    else:
        console.print(f"[red]✗[/red] {message}", style="red")
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Force kill without graceful shutdown")
def stop(name: str, force: bool) -> None:
    """Stop a running server."""
    manager = get_manager()
    success, message = manager.stop(name, force=force)
    
    if success:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]✗[/red] {message}", style="red")
        sys.exit(1)


@cli.command()
@click.argument("name")
def restart(name: str) -> None:
    """Restart a server."""
    manager = get_manager()
    success, message = manager.restart(name)
    
    if success:
        console.print(f"[green]✓[/green] {message}")
        server = manager.get_server(name)
        if server:
            console.print(f"    Logs: {server.log_file}")
    else:
        console.print(f"[red]✗[/red] {message}", style="red")
        sys.exit(1)


@cli.command(name="stop-all")
def stop_all() -> None:
    """Stop all running servers."""
    manager = get_manager()
    results = manager.stop_all()
    
    if not results:
        console.print("No running servers found")
        return
    
    for name, success, message in results:
        if success:
            console.print(f"[green]✓[/green] Stopped {name}")
        else:
            console.print(f"[red]✗[/red] Failed to stop {name}: {message}")


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def status(verbose: bool) -> None:
    """Show status of all servers."""
    manager = get_manager()
    servers = manager.list_servers()
    
    if not servers:
        console.print("No servers are currently managed")
        return
    
    table = Table(title="Backdrop Server Status")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("PID", justify="right")
    table.add_column("Uptime", justify="right")
    
    if verbose:
        table.add_column("CPU %", justify="right")
        table.add_column("Memory (MB)", justify="right")
        table.add_column("Command")
    
    for server in servers:
        is_running = server.is_running()
        status_text = Text("● Running", style="green") if is_running else Text("● Stopped", style="red")
        
        row = [
            server.name,
            status_text,
            str(server.pid) if server.pid else "-",
        ]
        
        if is_running:
            stats = server.get_stats()
            if stats:
                row.append(format_uptime(stats["uptime"]))
                if verbose:
                    row.extend([
                        f"{stats['cpu_percent']:.1f}",
                        f"{stats['memory_mb']:.1f}",
                        " ".join(server.command)
                    ])
            else:
                row.append("-")
                if verbose:
                    row.extend(["-", "-", " ".join(server.command)])
        else:
            row.append("-")
            if verbose:
                row.extend(["-", "-", " ".join(server.command)])
        
        table.add_row(*row)
    
    console.print(table)


@cli.command()
def list() -> None:
    """List all managed servers (alias for status)."""
    ctx = click.get_current_context()
    ctx.invoke(status)


@cli.command()
@click.argument("name")
@click.option("--lines", "-n", type=int, default=50, help="Number of lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--error", "-e", is_flag=True, help="Show error log instead")
def logs(name: str, lines: int, follow: bool, error: bool) -> None:
    """View server logs."""
    manager = get_manager()
    server = manager.get_server(name)
    
    if not server:
        console.print(f"[red]Error:[/red] Server '{name}' not found")
        sys.exit(1)
    
    log_file = server.error_log_file if error else server.log_file
    if not log_file or not os.path.exists(log_file):
        console.print(f"[red]Error:[/red] Log file not found")
        sys.exit(1)
    
    if follow:
        # Follow logs with tail
        console.print(f"Following {log_file} (Ctrl+C to stop)...")
        try:
            os.system(f"tail -f {log_file}")
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped following logs[/yellow]")
    else:
        # Show last n lines
        try:
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                start_idx = max(0, len(all_lines) - lines)
                
                if all_lines[start_idx:]:
                    console.print(f"[dim]Last {lines} lines from {log_file}:[/dim]\n")
                    for line in all_lines[start_idx:]:
                        console.print(line.rstrip())
                else:
                    console.print(f"[yellow]Log file is empty[/yellow]")
        except Exception as e:
            console.print(f"[red]Error reading log file:[/red] {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    cli()