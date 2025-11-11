"""Version management for MoonBit toolchain."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.table import Table

from .utils import get_config_dir

console = Console()


@dataclass
class VersionInfo:
    """Information about an installed MoonBit version."""
    version: str
    installed_at: str
    backup_path: Optional[str] = None


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


def list_available_versions() -> List[str]:
    """
    List available MoonBit versions.

    Note: The MoonBit binaries server doesn't provide a version listing API.
    This function returns known version identifiers.
    """
    # Since the server only exposes 'latest', we can only track what we've installed
    versions = ["latest"]

    # Could potentially scrape or check for dated releases if the URL pattern is known
    # For now, we'll just return latest and suggest checking the website

    return versions


def fetch_available_versions() -> None:
    """Display available versions information."""
    console.print("[cyan]Available MoonBit Versions:[/cyan]\n")

    console.print("• [green]latest[/green] - Most recent stable release")
    console.print("\n[yellow]Note:[/yellow] MoonBit currently only provides 'latest' builds.")
    console.print("For specific version history, visit: https://www.moonbitlang.com/download")

    # Show locally installed versions
    manager = VersionManager()
    history = manager.get_history()

    if history:
        console.print("\n[cyan]Previously Installed Versions:[/cyan]")
        for v in history:
            console.print(f"  • {v.version} (installed {v.installed_at})")
