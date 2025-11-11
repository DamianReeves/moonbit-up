"""Unit tests for config module."""

import json
import pytest
from pathlib import Path
from moonbit_up.config import (
    Config,
    MirrorConfig,
    InstallationConfig,
    load_config,
    save_config,
    set_mirror,
    reset_config,
)


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".config" / "moonbit-up"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"

    # Mock get_config_path to return our temp config file
    monkeypatch.setattr("moonbit_up.config.get_config_path", lambda: config_file)

    return config_dir


class TestConfig:
    """Tests for Config dataclass."""

    def test_config_creation(self):
        """Test creating a Config object."""
        mirror = MirrorConfig(
            index_url="https://example.com/index.json",
            download_base_url="https://example.com/releases"
        )
        installation = InstallationConfig(
            backup_enabled=True,
            verify_checksums=True
        )
        config = Config(mirror=mirror, installation=installation)

        assert config.mirror.index_url == "https://example.com/index.json"
        assert config.installation.backup_enabled is True


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_creates_default_if_missing(self, temp_config_dir):
        """Test that load_config returns defaults if file doesn't exist."""
        config = load_config()

        assert config.mirror.index_url.startswith("https://raw.githubusercontent.com")
        assert config.installation.backup_enabled is True

    def test_load_config_reads_existing_file(self, temp_config_dir):
        """Test loading an existing config file."""
        config_file = temp_config_dir / "config.toml"
        config_content = """
[mirror]
index_url = "https://custom.com/index.json"
download_base_url = "https://custom.com/releases"

[installation]
backup_enabled = false
verify_checksums = false
"""
        config_file.write_text(config_content)

        config = load_config()

        assert config.mirror.index_url == "https://custom.com/index.json"
        assert config.mirror.download_base_url == "https://custom.com/releases"
        assert config.installation.backup_enabled is False
        assert config.installation.verify_checksums is False

    def test_load_config_handles_partial_config(self, temp_config_dir):
        """Test loading config with only some fields specified."""
        config_file = temp_config_dir / "config.toml"
        config_content = """
[mirror]
index_url = "https://custom.com/index.json"
"""
        config_file.write_text(config_content)

        config = load_config()

        assert config.mirror.index_url == "https://custom.com/index.json"
        # Should use default for download_base_url
        assert config.mirror.download_base_url is not None


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_file(self, temp_config_dir):
        """Test that save_config creates a TOML file."""
        config = load_config()
        save_config(config)

        config_file = temp_config_dir / "config.toml"
        assert config_file.exists()

        content = config_file.read_text()
        assert "[mirror]" in content
        assert "[installation]" in content

    def test_save_config_overwrites_existing(self, temp_config_dir):
        """Test that save_config overwrites existing config."""
        config_file = temp_config_dir / "config.toml"
        config_file.write_text("old content")

        config = load_config()
        save_config(config)

        content = config_file.read_text()
        assert "old content" not in content
        assert "[mirror]" in content


class TestSetMirror:
    """Tests for set_mirror function."""

    def test_set_mirror_index_url(self, temp_config_dir, capsys):
        """Test setting only index URL."""
        result = set_mirror(index_url="https://new-mirror.com/index.json")

        assert result is True

        # Verify config was updated
        config = load_config()
        assert config.mirror.index_url == "https://new-mirror.com/index.json"

    def test_set_mirror_download_url(self, temp_config_dir, capsys):
        """Test setting only download URL."""
        result = set_mirror(download_url="https://new-mirror.com/releases")

        assert result is True

        config = load_config()
        assert config.mirror.download_base_url == "https://new-mirror.com/releases"

    def test_set_mirror_both_urls(self, temp_config_dir, capsys):
        """Test setting both URLs."""
        result = set_mirror(
            index_url="https://mirror.com/index.json",
            download_url="https://mirror.com/releases"
        )

        assert result is True

        config = load_config()
        assert config.mirror.index_url == "https://mirror.com/index.json"
        assert config.mirror.download_base_url == "https://mirror.com/releases"


class TestResetConfig:
    """Tests for reset_config function."""

    def test_reset_config_restores_defaults(self, temp_config_dir):
        """Test that reset_config restores default values."""
        # First, set custom values
        set_mirror(index_url="https://custom.com/index.json")

        # Verify custom value
        config = load_config()
        assert config.mirror.index_url == "https://custom.com/index.json"

        # Reset
        result = reset_config()
        assert result is True

        # Verify defaults restored
        config = load_config()
        assert config.mirror.index_url.startswith("https://raw.githubusercontent.com")


class TestDefaultConfig:
    """Tests for default configuration."""

    def test_load_config_returns_valid_defaults(self, temp_config_dir):
        """Test that default config has valid values."""
        config = load_config()

        assert isinstance(config, Config)
        assert isinstance(config.mirror, MirrorConfig)
        assert isinstance(config.installation, InstallationConfig)

        assert config.mirror.index_url.startswith("https://")
        assert config.mirror.download_base_url.startswith("https://")
        assert config.installation.backup_enabled is True
        assert config.installation.verify_checksums is True
