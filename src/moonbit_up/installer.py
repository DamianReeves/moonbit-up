"""MoonBit toolchain installer."""

import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

import requests

from .utils import (
    get_moon_home,
    ensure_amd64_libs,
    backup_moon_home,
    setup_wrappers,
    get_current_version,
)
from .version import VersionManager, list_available_versions

console = Console()

MOONBIT_BASE_URL = "https://cli.moonbitlang.com/binaries"
MOONBIT_BINARIES_GITHUB_URL = "https://github.com/chawyehsu/moonbit-binaries/releases/download"


class MoonBitInstaller:
    """Handles MoonBit toolchain installation."""

    def __init__(self):
        self.moon_home = get_moon_home()
        self.version_manager = VersionManager()

    def resolve_version(self, version: str) -> tuple[str, str]:
        """
        Resolve a version string to a download URL and actual version.

        Args:
            version: Version string ('latest' or specific version like '0.1.20241223+62b9a1a85')

        Returns:
            Tuple of (download_url, resolved_version)
        """
        if version == "latest":
            # Get the latest version from moonbit-binaries
            available = list_available_versions(limit=1)
            if available:
                ver = available[0]
                url = f"{MOONBIT_BINARIES_GITHUB_URL}/v{ver.version}/{ver.filename}"
                return url, ver.version
            else:
                # Fallback to official server
                console.print("[yellow]Could not fetch version list, using official server[/yellow]")
                return f"{MOONBIT_BASE_URL}/latest/moonbit-linux-x86_64.tar.gz", "latest"
        else:
            # Specific version requested
            available = list_available_versions()
            matching = [v for v in available if v.version == version]

            if matching:
                ver = matching[0]
                url = f"{MOONBIT_BINARIES_GITHUB_URL}/v{ver.version}/{ver.filename}"
                return url, ver.version
            else:
                console.print(f"[yellow]Version {version} not found in index, trying direct URL[/yellow]")
                # Try to construct URL anyway
                filename = f"moonbit-v{version}-linux-x64.tar.gz"
                url = f"{MOONBIT_BINARIES_GITHUB_URL}/v{version}/{filename}"
                return url, version

    def get_download_url(self, version: str = "latest") -> str:
        """Get the download URL for a specific version."""
        url, _ = self.resolve_version(version)
        return url

    def download_toolchain(self, version: str = "latest") -> Optional[Path]:
        """Download the MoonBit toolchain."""
        url = self.get_download_url(version)
        console.print(f"[cyan]Downloading MoonBit toolchain ({version})...[/cyan]")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            # Create temporary file
            temp_dir = Path(tempfile.mkdtemp())
            tar_path = temp_dir / "moonbit.tar.gz"

            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            with open(tar_path, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console
                    ) as progress:
                        task = progress.add_task("Downloading...", total=total_size)
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.update(task, completed=downloaded)

            console.print("[green]Download complete[/green]")
            return tar_path

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error downloading toolchain: {e}[/red]")
            return None

    def extract_toolchain(self, tar_path: Path, dest: Path) -> bool:
        """Extract the toolchain archive."""
        console.print("[cyan]Extracting toolchain...[/cyan]")

        try:
            with tarfile.open(tar_path, 'r:gz') as tar:
                # Extract to temporary location first
                temp_extract = tar_path.parent / "extract"
                temp_extract.mkdir(exist_ok=True)

                tar.extractall(temp_extract)

                # Move files to destination
                # The archive extracts to bin/, lib/, include/ directories
                for item in ["bin", "lib", "include"]:
                    src = temp_extract / item
                    if src.exists():
                        dst = dest / item
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)

            console.print("[green]Extraction complete[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Error extracting toolchain: {e}[/red]")
            return False

    def preserve_user_data(self, backup_path: Optional[Path]) -> None:
        """Preserve user data like registry and credentials from backup."""
        if not backup_path or not backup_path.exists():
            return

        # Preserve registry
        backup_registry = backup_path / "registry"
        if backup_registry.exists():
            dest_registry = self.moon_home / "registry"
            if dest_registry.exists():
                shutil.rmtree(dest_registry)
            shutil.copytree(backup_registry, dest_registry)
            console.print("[green]Preserved registry data[/green]")

        # Preserve credentials
        backup_creds = backup_path / "credentials.json"
        if backup_creds.exists():
            dest_creds = self.moon_home / "credentials.json"
            shutil.copy2(backup_creds, dest_creds)
            console.print("[green]Preserved credentials[/green]")

        # Preserve core library if it exists in backup but not in new installation
        backup_core = backup_path / "lib" / "core"
        dest_core = self.moon_home / "lib" / "core"
        if backup_core.exists() and not dest_core.exists():
            shutil.copytree(backup_core, dest_core)
            console.print("[green]Preserved core library[/green]")

    def verify_installation(self) -> bool:
        """Verify the installation by running moon version."""
        console.print("[cyan]Verifying installation...[/cyan]")

        moon_bin = self.moon_home / "bin" / "moon"
        if not moon_bin.exists():
            console.print("[red]Error: moon binary not found[/red]")
            return False

        try:
            result = subprocess.run(
                [str(moon_bin), "version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                console.print(f"[green]Installation verified: {version}[/green]")
                return True
            else:
                console.print(f"[red]Verification failed: {result.stderr}[/red]")
                return False

        except Exception as e:
            console.print(f"[red]Error verifying installation: {e}[/red]")
            return False

    def install(self, version: str = "latest", skip_backup: bool = False) -> bool:
        """Install or update MoonBit toolchain."""
        console.print("[bold cyan]MoonBit Toolchain Installer[/bold cyan]\n")

        # Resolve version
        console.print(f"Resolving version: {version}")
        _, resolved_version = self.resolve_version(version)
        console.print(f"Target version: {resolved_version}\n")

        # Check current version
        current = get_current_version()
        if current:
            console.print(f"Current version: {current}")
            if current == resolved_version:
                console.print("[yellow]Already at target version[/yellow]")
                return True

        # Ensure AMD64 libraries are set up
        if not ensure_amd64_libs():
            return False

        # Create backup if requested and installation exists
        backup_path = None
        if not skip_backup and self.moon_home.exists():
            backup_path = backup_moon_home()

        # Download toolchain
        tar_path = self.download_toolchain(version)
        if not tar_path:
            return False

        try:
            # Extract to moon home
            if not self.extract_toolchain(tar_path, self.moon_home):
                return False

            # Preserve user data
            self.preserve_user_data(backup_path)

            # Set up wrapper scripts
            setup_wrappers(self.moon_home)

            # Verify installation
            if not self.verify_installation():
                console.print("[red]Installation verification failed[/red]")
                return False

            # Record version in history
            installed_version = get_current_version()
            if installed_version:
                self.version_manager.add_version(installed_version, backup_path)

            console.print("\n[bold green]Installation complete![/bold green]")
            console.print(f"MoonBit toolchain installed at: {self.moon_home}")

            return True

        finally:
            # Cleanup
            if tar_path.parent != self.moon_home:
                shutil.rmtree(tar_path.parent, ignore_errors=True)

    def rollback(self) -> bool:
        """Rollback to the previous version."""
        console.print("[bold cyan]Rolling back MoonBit installation[/bold cyan]\n")

        # Get previous version info
        previous = self.version_manager.get_previous_version()
        if not previous:
            console.print("[yellow]No previous version found to rollback to[/yellow]")
            return False

        if not previous.backup_path:
            console.print("[red]No backup available for rollback[/red]")
            return False

        backup_path = Path(previous.backup_path)
        if not backup_path.exists():
            console.print(f"[red]Backup not found at {backup_path}[/red]")
            return False

        console.print(f"Rolling back to version: {previous.version}")

        try:
            # Remove current installation
            if self.moon_home.exists():
                shutil.rmtree(self.moon_home)

            # Restore from backup
            shutil.copytree(backup_path, self.moon_home, symlinks=True)

            console.print("[green]Rollback successful[/green]")

            # Verify
            self.verify_installation()

            return True

        except Exception as e:
            console.print(f"[red]Error during rollback: {e}[/red]")
            return False
