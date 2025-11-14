"""Configuration management for moonbit-up."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from rich.console import Console

import tomllib

console = Console()

# Default configuration
DEFAULT_CONFIG = {
    "mirror": {
        "index_url": "https://raw.githubusercontent.com/chawyehsu/moonbit-binaries/gh-pages/index.json",
        "download_base_url": "https://github.com/chawyehsu/moonbit-binaries/releases/download",
    },
    "nightly": {
        "dist_server": "https://moonup.csu.moe/v3",
    },
    "installation": {
        "backup_enabled": True,
        "verify_checksums": True,
    },
}


@dataclass
class MirrorConfig:
    """Mirror configuration."""
    index_url: str
    download_base_url: str


@dataclass
class NightlyConfig:
    """Nightly channel configuration."""
    dist_server: str


@dataclass
class InstallationConfig:
    """Installation configuration."""
    backup_enabled: bool
    verify_checksums: bool


@dataclass
class Config:
    """Main configuration object."""
    mirror: MirrorConfig
    nightly: NightlyConfig
    installation: InstallationConfig

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mirror": asdict(self.mirror),
            "nightly": asdict(self.nightly),
            "installation": asdict(self.installation),
        }


def get_config_path() -> Path:
    """Get the configuration file path."""
    config_dir = Path.home() / ".config" / "moonbit-up"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.toml"


def load_config() -> Config:
    """Load configuration from file or return default."""
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)

            # Merge with defaults (in case of missing keys)
            mirror_data = {**DEFAULT_CONFIG["mirror"], **data.get("mirror", {})}
            nightly_data = {**DEFAULT_CONFIG["nightly"], **data.get("nightly", {})}
            installation_data = {**DEFAULT_CONFIG["installation"], **data.get("installation", {})}

            return Config(
                mirror=MirrorConfig(**mirror_data),
                nightly=NightlyConfig(**nightly_data),
                installation=InstallationConfig(**installation_data),
            )
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")
            console.print("[yellow]Using default configuration[/yellow]")

    # Return default config
    return Config(
        mirror=MirrorConfig(**DEFAULT_CONFIG["mirror"]),
        nightly=NightlyConfig(**DEFAULT_CONFIG["nightly"]),
        installation=InstallationConfig(**DEFAULT_CONFIG["installation"]),
    )


def save_config(config: Config) -> bool:
    """Save configuration to file."""
    config_path = get_config_path()

    try:
        # Convert to TOML format
        toml_content = _config_to_toml(config)

        with open(config_path, "w") as f:
            f.write(toml_content)

        console.print(f"[green]Configuration saved to {config_path}[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Error saving configuration: {e}[/red]")
        return False


def _config_to_toml(config: Config) -> str:
    """Convert Config object to TOML string."""
    toml_lines = [
        "# moonbit-up configuration",
        "",
        "[mirror]",
        f'index_url = "{config.mirror.index_url}"',
        f'download_base_url = "{config.mirror.download_base_url}"',
        "",
        "[nightly]",
        f'dist_server = "{config.nightly.dist_server}"',
        "",
        "[installation]",
        f'backup_enabled = {str(config.installation.backup_enabled).lower()}',
        f'verify_checksums = {str(config.installation.verify_checksums).lower()}',
        "",
    ]
    return "\n".join(toml_lines)


def set_mirror(index_url: Optional[str] = None, download_url: Optional[str] = None) -> bool:
    """Set custom mirror URLs."""
    config = load_config()

    if index_url:
        config.mirror.index_url = index_url
        console.print(f"[green]Index URL updated:[/green] {index_url}")

    if download_url:
        config.mirror.download_base_url = download_url
        console.print(f"[green]Download URL updated:[/green] {download_url}")

    return save_config(config)


def reset_config() -> bool:
    """Reset configuration to defaults."""
    config = Config(
        mirror=MirrorConfig(**DEFAULT_CONFIG["mirror"]),
        nightly=NightlyConfig(**DEFAULT_CONFIG["nightly"]),
        installation=InstallationConfig(**DEFAULT_CONFIG["installation"]),
    )
    return save_config(config)


def show_config() -> None:
    """Display current configuration."""
    config = load_config()
    config_path = get_config_path()

    console.print(f"[bold cyan]Configuration[/bold cyan] ({config_path})\n")

    console.print("[bold]Mirror Settings:[/bold]")
    console.print(f"  Index URL:        {config.mirror.index_url}")
    console.print(f"  Download Base:    {config.mirror.download_base_url}")

    console.print("\n[bold]Nightly Settings:[/bold]")
    console.print(f"  Dist Server:      {config.nightly.dist_server}")

    console.print("\n[bold]Installation Settings:[/bold]")
    console.print(f"  Backup Enabled:   {config.installation.backup_enabled}")
    console.print(f"  Verify Checksums: {config.installation.verify_checksums}")
