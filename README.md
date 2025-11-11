# moonbit-up

A MoonBit toolchain manager for ARM64 systems with QEMU emulation support.

## Overview

`moonbit-up` automates the installation and management of the MoonBit toolchain on ARM64 systems (like Apple Silicon or ARM64 WSL2) where native ARM64 builds are not available. It handles:

- Downloading the AMD64 MoonBit toolchain
- Setting up QEMU user-mode emulation
- Extracting AMD64 system libraries from Docker
- Creating wrapper scripts for transparent execution
- Managing multiple versions and rollbacks

## Installation

Using `uv` (recommended - fast and modern):

```bash
cd ~/tools/moonbit-up
uv tool install -e .
```

Or using `pip`:

```bash
cd ~/tools/moonbit-up
pip install --user -e .
```

This will install the `moonbit-up` command to `~/.local/bin`.

## Usage

### Install or Update (Default Command)

Install the latest MoonBit toolchain:

```bash
moonbit-up
```

Or explicitly:

```bash
moonbit-up update
```

Install a specific version:

```bash
moonbit-up update v0.1.20251030
```

### List Available Versions

```bash
moonbit-up list
```

Shows available versions and previously installed versions.

### Show Current Version

```bash
moonbit-up current
```

Displays the currently installed MoonBit version.

### View Installation History

```bash
moonbit-up history
```

Shows all previously installed versions with timestamps.

### Rollback to Previous Version

```bash
moonbit-up rollback
```

Restores the most recent backup of your MoonBit installation.

## How It Works

1. **QEMU Emulation**: Uses QEMU user-mode to run AMD64 binaries on ARM64
2. **Library Setup**: Extracts AMD64 system libraries from Ubuntu Docker container
3. **Wrapper Scripts**: Creates bash wrappers that set `QEMU_LD_PREFIX` for each tool
4. **Version Tracking**: Maintains installation history in `~/.config/moonbit-up/`
5. **Smart Backups**: Automatically backs up before updates, preserving registry and credentials

## Directory Structure

```
~/.moon/                          # MoonBit installation
├── bin/                          # Executables (with wrappers)
├── lib/                          # Runtime libraries
├── include/                      # Header files
└── registry/                     # Package registry

~/moonbit-amd64-libs/             # AMD64 system libraries
├── lib/                          # x86_64 libraries
└── lib64/                        # Dynamic linker

~/.config/moonbit-up/             # Configuration
└── version_history.json          # Installation history

~/.moon.backup.YYYYMMDD_HHMMSS/   # Automatic backups
```

## Requirements

- Python 3.8+
- Docker (for extracting AMD64 libraries)
- QEMU user-mode emulation (automatically set up)

## Development

To modify the tool:

```bash
cd ~/tools/moonbit-up
# Make changes to src/moonbit_up/*.py
uv tool install -e .  # Reinstall in development mode
```

To uninstall:

```bash
uv tool uninstall moonbit-up
```

## Troubleshooting

### Command not found

Ensure `~/.local/bin` is in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add to your `~/.bashrc` to make it permanent.

### QEMU errors

If you see "Could not open '/lib64/ld-linux-x86-64.so.2'" errors, reinstall to set up AMD64 libraries:

```bash
moonbit-up update
```

### Docker not available

Docker is required for initial setup to extract AMD64 libraries. Ensure Docker is installed and running.

## License

MIT
