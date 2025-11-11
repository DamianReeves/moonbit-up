"""CLI interface for moonbit-up."""

import typer
from typing import Optional
from rich.console import Console

from .installer import MoonBitInstaller
from .version import VersionManager, fetch_available_versions
from .utils import get_current_version

app = typer.Typer(
    name="moonbit-up",
    help="MoonBit toolchain manager for ARM64 systems with QEMU emulation",
    add_completion=False,
)

console = Console()


@app.command()
def update(
    version: str = typer.Argument(
        "latest",
        help="Version to install (default: latest)"
    ),
    no_backup: bool = typer.Option(
        False,
        "--no-backup",
        help="Skip creating a backup of the current installation"
    ),
):
    """
    Install or update MoonBit toolchain.

    This is the default command when no subcommand is specified.
    """
    installer = MoonBitInstaller()
    success = installer.install(version=version, skip_backup=no_backup)

    if success:
        console.print("\n[green]✓[/green] Run [cyan]moon version[/cyan] to verify the installation")
        raise typer.Exit(0)
    else:
        console.print("\n[red]✗[/red] Installation failed")
        raise typer.Exit(1)


@app.command("list")
def list_versions(
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all available versions (not just recent 20)"
    )
):
    """
    List available MoonBit versions.

    Shows available versions that can be installed from moonbit-binaries,
    as well as previously installed versions tracked locally.
    """
    fetch_available_versions(show_all=all)


@app.command()
def current():
    """
    Show the currently installed MoonBit version.
    """
    version = get_current_version()

    if version:
        console.print(f"[green]Current MoonBit version:[/green] {version}")

        # Also show installation history
        console.print("\n[cyan]Installation history:[/cyan]")
        manager = VersionManager()
        manager.show_history()
    else:
        console.print("[yellow]MoonBit is not currently installed[/yellow]")
        console.print("Run [cyan]moonbit-up[/cyan] to install it")
        raise typer.Exit(1)


@app.command()
def rollback():
    """
    Rollback to the previous MoonBit installation.

    Restores the most recent backup of the MoonBit toolchain.
    """
    installer = MoonBitInstaller()
    success = installer.rollback()

    if success:
        raise typer.Exit(0)
    else:
        raise typer.Exit(1)


@app.command()
def history():
    """
    Show installation history.

    Displays all previously installed versions with their installation dates.
    """
    manager = VersionManager()
    manager.show_history()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version information"
    ),
):
    """
    MoonBit toolchain manager for ARM64 systems.

    Run without arguments to install/update to the latest version,
    or use one of the subcommands for more control.
    """
    if version:
        from . import __version__
        console.print(f"moonbit-up version {__version__}")
        raise typer.Exit(0)

    # If no subcommand was specified, run update
    if ctx.invoked_subcommand is None:
        update()


if __name__ == "__main__":
    app()
