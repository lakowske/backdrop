"""Command-line interface for backdrop."""

import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from backdrop import __version__
from backdrop.logger import setup_logger, tail_log_file
from backdrop.process import ProcessManager

console = Console()
logger = setup_logger("backdrop.cli")


@click.group()
@click.version_option(version=__version__, prog_name="backdrop")
@click.option(
    "--cwd",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Working directory for backdrop operations",
)
@click.option(
    "--start-verify-delay",
    type=float,
    default=0.25,
    help="Delay after starting to verify process (default: 0.25s)",
)
@click.option(
    "--restart-delay",
    type=float,
    default=0.5,
    help="Delay between stop and start during restart (default: 0.5s)",
)
@click.option(
    "--log-poll-interval",
    type=float,
    default=0.05,
    help="Polling interval for log following (default: 0.05s)",
)
@click.pass_context
def cli(
    ctx: click.Context,
    cwd: Optional[Path],
    start_verify_delay: float,
    restart_delay: float,
    log_poll_interval: float,
) -> None:
    """Backdrop - Simple server daemon manager.

    Run any server in the background with automatic logging.
    """
    ctx.ensure_object(dict)
    ctx.obj["manager"] = ProcessManager(
        base_dir=cwd,
        start_verify_delay=start_verify_delay,
        restart_delay=restart_delay,
        log_poll_interval=log_poll_interval,
    )
    logger.info(
        f"CLI initialized - version={__version__}, cwd={cwd}, "
        f"start_verify_delay={start_verify_delay}s, "
        f"restart_delay={restart_delay}s, "
        f"log_poll_interval={log_poll_interval}s"
    )


@cli.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--name", "-n", help="Process name (default: command name)")
@click.pass_context
def start(ctx: click.Context, command: List[str], name: Optional[str]) -> None:
    """Start a server in the background.

    COMMAND is the command and arguments to run.
    """
    manager: ProcessManager = ctx.obj["manager"]
    logger.info(f"Start command - command={' '.join(command)}, name={name}")

    pid = manager.start(list(command), name)
    if pid:
        sys.exit(0)
    else:
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option("--timeout", "-t", default=5, help="Timeout in seconds")
@click.pass_context
def stop(ctx: click.Context, name: str, timeout: int) -> None:
    """Stop a running server."""
    manager: ProcessManager = ctx.obj["manager"]
    logger.info(f"Stop command - name={name}, timeout={timeout}")

    if manager.stop(name, timeout):
        sys.exit(0)
    else:
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option("--timeout", "-t", default=5, help="Timeout in seconds")
@click.pass_context
def restart(ctx: click.Context, name: str, timeout: int) -> None:
    """Restart a server."""
    manager: ProcessManager = ctx.obj["manager"]
    logger.info(f"Restart command - name={name}, timeout={timeout}")

    pid = manager.restart(name, timeout)
    if pid:
        sys.exit(0)
    else:
        sys.exit(1)


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def status(ctx: click.Context, verbose: bool) -> None:
    """Show status of all servers."""
    manager: ProcessManager = ctx.obj["manager"]
    logger.info(f"Status command - verbose={verbose}")

    processes = manager.status(verbose)

    if not processes:
        console.print("No servers are running.", style="yellow")
        return

    # Create table
    table = Table(title="Running Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("PID", justify="right")
    table.add_column("Uptime", justify="right")

    if verbose:
        table.add_column("CPU", justify="right")
        table.add_column("Memory", justify="right")
        table.add_column("Command", style="dim")

    # Add rows
    for proc in processes:
        row = [
            proc["name"],
            f"● {proc['status'].title()}",
            str(proc["pid"]),
            proc["uptime"],
        ]

        if verbose:
            row.extend(
                [
                    proc.get("cpu_percent", "0.0%"),
                    proc.get("memory", "0 B"),
                    proc.get("command", ""),
                ]
            )

        table.add_row(*row)

    console.print(table)


@cli.command()
@click.argument("name")
@click.option("--lines", "-n", default=20, help="Number of lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--error", "-e", is_flag=True, help="Show error log instead")
@click.pass_context
def logs(ctx: click.Context, name: str, lines: int, follow: bool, error: bool) -> None:
    """View server logs."""
    manager: ProcessManager = ctx.obj["manager"]
    logger.info(f"Logs command - name={name}, lines={lines}, follow={follow}, error={error}")

    stdout_log, stderr_log = manager.get_log_files(name)

    log_file = stderr_log if error else stdout_log

    if not log_file:
        console.print(f"No log file found for {name}", style="red")
        sys.exit(1)

    console.print(f"Showing logs from: {log_file}", style="dim")
    console.print("-" * 60)

    tail_log_file(log_file, lines, follow, manager.log_poll_interval)


@cli.command(name="stop-all")
@click.option("--timeout", "-t", default=5, help="Timeout in seconds per server")
@click.confirmation_option(prompt="Stop all running servers?")
@click.pass_context
def stop_all(ctx: click.Context, timeout: int) -> None:
    """Stop all running servers."""
    manager: ProcessManager = ctx.obj["manager"]
    logger.info(f"Stop-all command - timeout={timeout}")

    stopped = manager.stop_all(timeout)
    console.print(f"Stopped {stopped} server(s).", style="green")


# Convenience aliases
@cli.command(hidden=True)
@click.argument("command", nargs=-1, required=True)
@click.option("--name", "-n", help="Process name")
@click.pass_context
def node(ctx: click.Context, command: List[str], name: Optional[str]) -> None:
    """Start a Node.js server (alias for 'start node')."""
    full_command = ["node", *list(command)]
    ctx.invoke(start, command=full_command, name=name)


@cli.command(hidden=True)
@click.argument("command", nargs=-1, required=True)
@click.option("--name", "-n", help="Process name")
@click.pass_context
def python(ctx: click.Context, command: List[str], name: Optional[str]) -> None:
    """Start a Python server (alias for 'start python')."""
    full_command = ["python", *list(command)]
    ctx.invoke(start, command=full_command, name=name)


if __name__ == "__main__":
    cli()
