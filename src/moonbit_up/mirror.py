"""Mirror setup and management for moonbit-binaries."""

import json
import shutil
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

import requests

from .version import fetch_moonbit_binaries_index, list_available_versions
from .config import load_config

console = Console()


class MirrorManager:
    """Manages local mirrors of moonbit-binaries."""

    def __init__(self, mirror_path: Path):
        self.mirror_path = mirror_path
        self.releases_dir = mirror_path / "releases"
        self.index_file = mirror_path / "index.json"

    def create_mirror(self, versions: Optional[List[str]] = None, all_versions: bool = False) -> bool:
        """
        Create or update a local mirror of moonbit-binaries.

        Args:
            versions: Specific versions to download (None for latest only)
            all_versions: Download all available versions

        Returns:
            True if successful
        """
        console.print("[bold cyan]Setting up MoonBit Binaries Mirror[/bold cyan]\n")

        # Create directory structure
        self.mirror_path.mkdir(parents=True, exist_ok=True)
        self.releases_dir.mkdir(exist_ok=True)

        # Fetch version index
        console.print("Fetching version index...")
        available = list_available_versions()

        if not available:
            console.print("[red]Error: Could not fetch version list[/red]")
            return False

        # Determine which versions to mirror
        if all_versions:
            versions_to_mirror = available
            console.print(f"[green]Mirroring all {len(available)} versions[/green]\n")
        elif versions:
            versions_to_mirror = [v for v in available if v.version in versions]
            if not versions_to_mirror:
                console.print(f"[red]Error: None of the specified versions found[/red]")
                return False
            console.print(f"[green]Mirroring {len(versions_to_mirror)} specified versions[/green]\n")
        else:
            # Default: mirror only the latest
            versions_to_mirror = available[:1]
            console.print("[green]Mirroring latest version only[/green]\n")

        # Download binaries
        config = load_config()
        download_base = config.mirror.download_base_url

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Downloading binaries...", total=len(versions_to_mirror))

            for ver in versions_to_mirror:
                version_dir = self.releases_dir / f"v{ver.version}"
                version_dir.mkdir(parents=True, exist_ok=True)
                binary_path = version_dir / ver.filename

                # Skip if already exists
                if binary_path.exists():
                    progress.console.print(f"[dim]Skipping {ver.version} (already exists)[/dim]")
                    progress.advance(task)
                    continue

                # Download binary
                url = f"{download_base}/v{ver.version}/{ver.filename}"
                try:
                    response = requests.get(url, stream=True, timeout=30)
                    response.raise_for_status()

                    with open(binary_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    progress.console.print(f"[green]Downloaded {ver.version}[/green]")
                except Exception as e:
                    progress.console.print(f"[red]Error downloading {ver.version}: {e}[/red]")

                progress.advance(task)

        # Create local index.json
        self._create_index(versions_to_mirror)

        console.print(f"\n[bold green]Mirror created successfully![/bold green]")
        console.print(f"Location: {self.mirror_path}")
        console.print(f"\nTo use this mirror, run:")
        console.print(f'  moonbit-up config --index-url "file://{self.index_file}"')
        console.print(f'  moonbit-up config --download-url "file://{self.releases_dir}"')

        return True

    def _create_index(self, versions: List) -> None:
        """Create a local index.json file."""
        from datetime import datetime

        index_data = {
            "linux-x64": {
                "last_modified": datetime.now().isoformat(),
                "releases": [
                    {
                        "version": v.version,
                        "name": v.filename,
                        "sha256": v.sha256
                    }
                    for v in versions
                ]
            }
        }

        with open(self.index_file, 'w') as f:
            json.dump(index_data, f, indent=2)

        console.print(f"[green]Created index: {self.index_file}[/green]")

    def serve_mirror(self, port: int = 8000) -> None:
        """
        Serve the mirror via HTTP (for testing/local network).

        Args:
            port: Port to serve on
        """
        import http.server
        import socketserver
        import os

        os.chdir(self.mirror_path)

        handler = http.server.SimpleHTTPRequestHandler

        console.print(f"[cyan]Starting mirror server on port {port}...[/cyan]")
        console.print(f"Mirror URL: http://localhost:{port}/")
        console.print(f"Index URL:  http://localhost:{port}/index.json")
        console.print(f"To use, run:")
        console.print(f'  moonbit-up config --index-url "http://localhost:{port}/index.json"')
        console.print(f'  moonbit-up config --download-url "http://localhost:{port}/releases"')
        console.print("\n[yellow]Press Ctrl+C to stop the server[/yellow]\n")

        try:
            with socketserver.TCPServer(("", port), handler) as httpd:
                httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Server stopped[/yellow]")

    def sync_mirror(self) -> bool:
        """
        Sync mirror with upstream to get new versions.

        Returns:
            True if successful
        """
        if not self.index_file.exists():
            console.print("[red]Error: Mirror not initialized. Run 'mirror create' first.[/red]")
            return False

        console.print("[cyan]Syncing mirror with upstream...[/cyan]\n")

        # Load local index
        with open(self.index_file, 'r') as f:
            local_index = json.load(f)

        local_versions = {r['version'] for r in local_index['linux-x64']['releases']}

        # Fetch upstream versions
        upstream_versions = list_available_versions()
        upstream_version_set = {v.version for v in upstream_versions}

        # Find new versions
        new_versions = upstream_version_set - local_versions

        if not new_versions:
            console.print("[green]Mirror is up to date![/green]")
            return True

        console.print(f"[yellow]Found {len(new_versions)} new versions to sync[/yellow]")

        # Download new versions
        new_version_objs = [v for v in upstream_versions if v.version in new_versions]

        config = load_config()
        download_base = config.mirror.download_base_url

        for ver in new_version_objs:
            version_dir = self.releases_dir / f"v{ver.version}"
            version_dir.mkdir(parents=True, exist_ok=True)
            binary_path = version_dir / ver.filename

            url = f"{download_base}/v{ver.version}/{ver.filename}"

            try:
                console.print(f"Downloading {ver.version}...")
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()

                with open(binary_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                console.print(f"[green]✓ {ver.version}[/green]")
            except Exception as e:
                console.print(f"[red]✗ {ver.version}: {e}[/red]")

        # Update index
        all_versions = [v for v in upstream_versions if v.version in (local_versions | new_versions)]
        self._create_index(all_versions)

        console.print(f"\n[bold green]Sync complete![/bold green]")
        return True

    def info(self) -> None:
        """Display information about the mirror."""
        if not self.mirror_path.exists():
            console.print("[yellow]Mirror not set up at this location[/yellow]")
            return

        console.print(f"[bold cyan]Mirror Information[/bold cyan]\n")
        console.print(f"Location:     {self.mirror_path}")
        console.print(f"Releases Dir: {self.releases_dir}")
        console.print(f"Index File:   {self.index_file}")

        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                index = json.load(f)

            releases = index['linux-x64']['releases']
            console.print(f"\nVersions:     {len(releases)}")
            console.print(f"Last Updated: {index['linux-x64']['last_modified']}")

            if releases:
                console.print(f"\nLatest:       {releases[0]['version']}")
                console.print(f"Oldest:       {releases[-1]['version']}")
        else:
            console.print("\n[yellow]Index not created yet[/yellow]")

        # Calculate disk usage
        if self.releases_dir.exists():
            total_size = sum(f.stat().st_size for f in self.releases_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            console.print(f"\nDisk Usage:   {size_mb:.1f} MB")
