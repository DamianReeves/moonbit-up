"""CLI interface for moonbit-up."""

import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console

from .installer import MoonBitInstaller
from .version import VersionManager, fetch_available_versions
from .utils import get_current_version
from .config import show_config, set_mirror, reset_config
from .mirror import MirrorManager

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


@app.command()
def config(
    show: bool = typer.Option(
        False,
        "--show",
        help="Show current configuration"
    ),
    set_index_url: Optional[str] = typer.Option(
        None,
        "--index-url",
        help="Set custom index URL for version listings"
    ),
    set_download_url: Optional[str] = typer.Option(
        None,
        "--download-url",
        help="Set custom download base URL for binaries"
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Reset configuration to defaults"
    ),
):
    """
    Manage moonbit-up configuration.

    Configure custom mirrors for the MoonBit binaries index and downloads.
    Useful for setting up local mirrors or using alternative sources.
    """
    if reset:
        if reset_config():
            console.print("[green]Configuration reset to defaults[/green]")
            raise typer.Exit(0)
        else:
            raise typer.Exit(1)

    if set_index_url or set_download_url:
        if set_mirror(index_url=set_index_url, download_url=set_download_url):
            console.print("\n[green]Configuration updated successfully[/green]")
            show = True  # Show config after updating
        else:
            raise typer.Exit(1)

    if show or (not set_index_url and not set_download_url and not reset):
        # Default action: show config
        show_config()


@app.command()
def mirror(
    action: str = typer.Argument(
        ...,
        help="Action: create, sync, info, or serve"
    ),
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Path to mirror directory (default: ~/moonbit-mirror)"
    ),
    versions: Optional[List[str]] = typer.Option(
        None,
        "--version",
        "-v",
        help="Specific versions to mirror (can specify multiple)"
    ),
    all_versions: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Mirror all available versions"
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="Port for HTTP server (serve action only)"
    ),
):
    """
    Manage a local mirror of moonbit-binaries.

    Actions:
      create  - Create or update a mirror
      sync    - Sync mirror with upstream (get new versions)
      info    - Show mirror information
      serve   - Serve mirror via HTTP

    Examples:
      moonbit-up mirror create                    # Mirror latest version
      moonbit-up mirror create --all              # Mirror all versions
      moonbit-up mirror create -v 0.1.20241223+... # Mirror specific version
      moonbit-up mirror sync                       # Update mirror
      moonbit-up mirror serve --port 8080          # Serve on port 8080
      moonbit-up mirror info                       # Show mirror stats
    """
    if path is None:
        path = Path.home() / "moonbit-mirror"

    manager = MirrorManager(path)

    if action == "create":
        if manager.create_mirror(versions=versions, all_versions=all_versions):
            raise typer.Exit(0)
        else:
            raise typer.Exit(1)

    elif action == "sync":
        if manager.sync_mirror():
            raise typer.Exit(0)
        else:
            raise typer.Exit(1)

    elif action == "info":
        manager.info()

    elif action == "serve":
        manager.serve_mirror(port=port)

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Valid actions: create, sync, info, serve")
        raise typer.Exit(1)


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
