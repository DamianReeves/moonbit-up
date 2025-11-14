"""Utility functions for moonbit-up."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from rich.console import Console
import platform
import requests

console = Console()

def get_moon_home() -> Path:
    """Get the MoonBit home directory."""
    moon_home = os.environ.get("MOON_HOME", os.path.expanduser("~/.moon"))
    return Path(moon_home)

def get_config_dir() -> Path:
    """Get the moonbit-up config directory."""
    config_dir = Path.home() / ".config" / "moonbit-up"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_amd64_libs_dir() -> Path:
    """Get the AMD64 libraries directory."""
    return Path.home() / "moonbit-amd64-libs"

def ensure_amd64_libs() -> bool:
    """Ensure AMD64 libraries are set up for QEMU."""
    libs_dir = get_amd64_libs_dir()
    lib_dir = libs_dir / "lib"
    lib64_dir = libs_dir / "lib64"

    if lib_dir.exists() and lib64_dir.exists():
        ld_path = lib64_dir / "ld-linux-x86-64.so.2"
        if ld_path.exists():
            return True

    console.print("[yellow]AMD64 libraries not found. Setting up...[/yellow]")

    # Check if Docker is available
    if not shutil.which("docker"):
        console.print("[red]Error: Docker is required to set up AMD64 libraries[/red]")
        return False

    try:
        # Create directories
        lib_dir.mkdir(parents=True, exist_ok=True)
        lib64_dir.mkdir(parents=True, exist_ok=True)

        # Extract libraries from Ubuntu AMD64 container
        subprocess.run([
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "-v", f"{libs_dir}:/output",
            "ubuntu:24.04", "bash", "-c",
            "cp -r /lib/x86_64-linux-gnu/* /output/lib/ && cp /lib64/ld-linux-x86-64.so.2 /output/lib64/"
        ], check=True, capture_output=True)

        console.print("[green]AMD64 libraries set up successfully[/green]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error setting up AMD64 libraries: {e}[/red]")
        return False

def backup_moon_home(suffix: Optional[str] = None) -> Optional[Path]:
    """Create a backup of the current Moon installation."""
    moon_home = get_moon_home()
    if not moon_home.exists():
        return None

    if suffix is None:
        from datetime import datetime
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = moon_home.parent / f".moon.backup.{suffix}"

    try:
        shutil.copytree(moon_home, backup_path, symlinks=True)
        console.print(f"[green]Backup created at {backup_path}[/green]")
        return backup_path
    except Exception as e:
        console.print(f"[red]Error creating backup: {e}[/red]")
        return None

def get_current_version() -> Optional[str]:
    """Get the currently installed MoonBit version."""
    moon_home = get_moon_home()
    moon_bin = moon_home / "bin" / "moon"

    if not moon_bin.exists():
        return None

    try:
        result = subprocess.run(
            [str(moon_bin), "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse version from output like "moon 0.1.20251030 (cf54fca 2025-10-30)"
            output = result.stdout.strip()
            if output.startswith("moon "):
                version = output.split()[1]
                return version
    except Exception:
        pass

    return None

def detect_target_triple() -> str:
    """Detect the current OS/arch target triple used by nightly assets.

    Returns a Rust-like target triple string, e.g., 'x86_64-unknown-linux'.
    
    Note: For ARM64 Linux, returns x86_64 target since this tool is designed
    to run x86_64 binaries on ARM64 via QEMU emulation.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        # Always use x86_64 for Linux (ARM64 will use QEMU)
        return "x86_64-unknown-linux"
    elif system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        if machine in ("x86_64", "amd64"):
            return "x86_64-apple-darwin"
    elif system == "windows":
        if machine in ("x86_64", "amd64"):
            return "x86_64-pc-windows"
    # Fallback
    return f"{machine}-{system}"

def candidate_asset_names_for_triple(triple: str, date: Optional[str] = None) -> list[str]:
    """Generate candidate asset filenames for a given target triple.

    This accounts for common naming variations used across releases.
    Args:
        triple: Target triple like 'x86_64-unknown-linux'
        date: Optional date string for nightly builds (e.g., '2025-11-13')
    """
    ext = ".zip" if triple.endswith("pc-windows") else ".tar.gz"
    arch, _, os_part = triple.partition("-")
    # variations seen in community assets
    candidates = []
    
    if date:
        # Nightly pattern: moonbit-nightly-YYYY-MM-DD-triple.ext
        candidates.extend([
            f"moonbit-nightly-{date}-{triple}{ext}",
            f"moonbit-nightly-{date}-{os_part}-{arch}{ext}",
            f"moonbit-nightly-{date}-{arch}-{os_part}{ext}",
        ])
    
    # Standard patterns (for stable or fallback)
    candidates.extend([
        f"moonbit-{triple}{ext}",
        f"moonbit-{os_part}-{arch}{ext}",
        f"moonbit-{arch}-{os_part}{ext}",
    ])
    if os_part.startswith("unknown-linux"):
        if date:
            candidates.append(f"moonbit-nightly-{date}-linux-{arch}{ext}")
        candidates.append(f"moonbit-linux-{arch}{ext}")
    return candidates

def probe_first_existing_asset(base_url: str, tag: str, candidates: list[str]) -> Optional[str]:
    """Return the first asset name that exists (HTTP 200) under the given tag.

    Returns the resolved full URL if found, else None.
    """
    for name in candidates:
        url = f"{base_url}/{tag}/{name}"
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                return url
        except Exception:
            continue
    return None

def create_wrapper_script(binary_name: str, moon_home: Path) -> bool:
    """Create a wrapper script for a MoonBit binary."""
    bin_dir = moon_home / "bin"
    real_binary = bin_dir / f"{binary_name}.real"
    wrapper = bin_dir / binary_name

    if not real_binary.exists():
        return False

    wrapper_content = f'''#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
BINARY_NAME="$(basename "${{BASH_SOURCE[0]}}")"
export QEMU_LD_PREFIX="$HOME/moonbit-amd64-libs"
exec "$SCRIPT_DIR/$BINARY_NAME.real" "$@"
'''

    try:
        wrapper.write_text(wrapper_content)
        wrapper.chmod(0o755)
        return True
    except Exception as e:
        console.print(f"[red]Error creating wrapper for {binary_name}: {e}[/red]")
        return False

def setup_wrappers(moon_home: Path) -> None:
    """Set up wrapper scripts for all MoonBit binaries."""
    bin_dir = moon_home / "bin"
    binaries = [
        "moon", "moonc", "moonfmt", "mooninfo", "mooncake",
        "moon_cove_report", "moonbit-lsp", "moondoc", "moonrun", "moon-ide"
    ]

    for binary in binaries:
        binary_path = bin_dir / binary
        real_path = bin_dir / f"{binary}.real"

        # Skip if already wrapped
        if real_path.exists():
            continue

        # Skip if binary doesn't exist
        if not binary_path.exists():
            continue

        # Rename original to .real
        binary_path.rename(real_path)

        # Create wrapper
        create_wrapper_script(binary, moon_home)

    console.print("[green]Wrapper scripts created successfully[/green]")
