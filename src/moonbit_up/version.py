"""Version management for MoonBit toolchain."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.table import Table

import requests

from .utils import get_config_dir
from .config import load_config

console = Console()


@dataclass
class VersionInfo:
    """Information about an installed MoonBit version."""
    version: str
    installed_at: str
    backup_path: Optional[str] = None


@dataclass
class AvailableVersion:
    """Information about an available MoonBit version."""
    version: str
    filename: str
    sha256: str
    last_modified: Optional[str] = None


class VersionManager:
    """Manages MoonBit version history and rollbacks."""

    def __init__(self):
        self.config_dir = get_config_dir()
        self.history_file = self.config_dir / "version_history.json"
        self._ensure_history_file()

    def _ensure_history_file(self) -> None:
        """Ensure the history file exists."""
        if not self.history_file.exists():
            self.history_file.write_text(json.dumps({"versions": []}, indent=2))

    def _load_history(self) -> Dict:
        """Load the version history."""
        try:
            return json.loads(self.history_file.read_text())
        except Exception:
            return {"versions": []}

    def _save_history(self, history: Dict) -> None:
        """Save the version history."""
        self.history_file.write_text(json.dumps(history, indent=2))

    def add_version(self, version: str, backup_path: Optional[Path] = None) -> None:
        """Add a version to the history."""
        history = self._load_history()

        version_info = VersionInfo(
            version=version,
            installed_at=datetime.now().isoformat(),
            backup_path=str(backup_path) if backup_path else None
        )

        history["versions"].append(asdict(version_info))
        self._save_history(history)

    def get_history(self) -> List[VersionInfo]:
        """Get the version history."""
        history = self._load_history()
        return [VersionInfo(**v) for v in history["versions"]]

    def get_previous_version(self) -> Optional[VersionInfo]:
        """Get the previous version info for rollback."""
        history = self.get_history()
        if len(history) < 2:
            return None
        return history[-2]

    def show_history(self) -> None:
        """Display the version history."""
        history = self.get_history()

        if not history:
            console.print("[yellow]No version history found[/yellow]")
            return

        table = Table(title="MoonBit Version History")
        table.add_column("Version", style="cyan")
        table.add_column("Installed At", style="green")
        table.add_column("Backup", style="yellow")

        for version_info in history:
            installed = datetime.fromisoformat(version_info.installed_at)
            installed_str = installed.strftime("%Y-%m-%d %H:%M:%S")
            backup = "✓" if version_info.backup_path else "✗"
            table.add_row(version_info.version, installed_str, backup)

        console.print(table)


def fetch_moonbit_binaries_index() -> Optional[Dict]:
    """Fetch the moonbit-binaries index from configured mirror."""
    config = load_config()
    index_url = config.mirror.index_url

    try:
        console.print(f"[dim]Fetching from: {index_url}[/dim]")
        response = requests.get(index_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        console.print(f"[yellow]Warning: Could not fetch version index: {e}[/yellow]")
        return None


def list_available_versions(limit: Optional[int] = None) -> List[AvailableVersion]:
    """
    List available MoonBit versions from moonbit-binaries.

    Args:
        limit: Maximum number of versions to return (None for all)

    Returns:
        List of AvailableVersion objects
    """
    index = fetch_moonbit_binaries_index()
    if not index:
        return []

    linux_x64_data = index.get("linux-x64", {})
    releases = linux_x64_data.get("releases", [])
    last_modified = linux_x64_data.get("last_modified")

    versions = [
        AvailableVersion(
            version=r["version"],
            filename=r["name"],
            sha256=r["sha256"],
            last_modified=last_modified
        )
        for r in releases
    ]

    if limit:
        versions = versions[:limit]

    return versions


def fetch_available_versions(show_all: bool = False) -> None:
    """
    Display available versions information.

    Args:
        show_all: If True, show all versions. If False, show recent versions.
    """
    console.print("[bold cyan]Available MoonBit Versions[/bold cyan]")
    console.print("(from chawyehsu/moonbit-binaries)\n")

    versions = list_available_versions(limit=None if show_all else 20)

    if not versions:
        console.print("[red]Could not fetch available versions[/red]")
        console.print("Fallback: Use [green]'latest'[/green] to install the most recent version")
        return

    # Create table
    table = Table(title=f"{'All' if show_all else 'Recent'} Linux x86-64 Releases")
    table.add_column("#", style="dim", width=4)
    table.add_column("Version", style="cyan")
    table.add_column("Release Date", style="green")

    for idx, ver in enumerate(versions, 1):
        # Extract date from version string (format: 0.1.YYYYMMDD+hash)
        version_parts = ver.version.split("+")
        version_base = version_parts[0]
        date_part = version_base.split(".")[-1] if "." in version_base else ""

        # Try to parse date
        try:
            if len(date_part) == 8 and date_part.isdigit():
                date_obj = datetime.strptime(date_part, "%Y%m%d")
                date_str = date_obj.strftime("%Y-%m-%d")
            else:
                date_str = "Unknown"
        except:
            date_str = "Unknown"

        table.add_row(str(idx), ver.version, date_str)

    console.print(table)

    if not show_all and len(versions) == 20:
        console.print("\n[dim]Showing 20 most recent versions. Use --all flag to see all versions.[/dim]")

    console.print(f"\n[green]Total available versions:[/green] {len(versions)}")
    console.print("\n[cyan]Usage:[/cyan]")
    console.print("  moonbit-up update <version>  # Install specific version")
    console.print("  moonbit-up update latest     # Install most recent version")

    # Show locally installed versions
    manager = VersionManager()
    history = manager.get_history()

    if history:
        console.print("\n[cyan]Previously Installed Versions:[/cyan]")
        for v in history:
            installed = datetime.fromisoformat(v.installed_at).strftime("%Y-%m-%d %H:%M")
            console.print(f"  • {v.version} (installed {installed})")
