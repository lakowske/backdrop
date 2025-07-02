"""Entry point for backdrop CLI."""

from backdrop.cli import cli


def main() -> None:
    """Main entry point."""
    cli(prog_name="bd")


if __name__ == "__main__":
    main()