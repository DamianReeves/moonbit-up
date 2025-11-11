"""Unit tests for version module."""

import json
import pytest
import responses
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from moonbit_up.version import (
    VersionInfo,
    AvailableVersion,
    VersionManager,
    fetch_moonbit_binaries_index,
    list_available_versions,
)


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".config" / "moonbit-up"
    config_dir.mkdir(parents=True)
    monkeypatch.setattr("moonbit_up.version.get_config_dir", lambda: config_dir)
    return config_dir


@pytest.fixture
def sample_index():
    """Sample moonbit-binaries index data."""
    return {
        "linux-x64": {
            "last_modified": "2024-12-23T10:00:00",
            "releases": [
                {
                    "version": "0.1.20241223+62b9a1a85",
                    "name": "moonbit-v0.1.20241223+62b9a1a85-linux-x64.tar.gz",
                    "sha256": "e613706d44dea09c4089b137884fc64ce6b9ce0e43661778432eeaa8b6c6d519"
                },
                {
                    "version": "0.1.20241218+f4a066f5f",
                    "name": "moonbit-v0.1.20241218+f4a066f5f-linux-x64.tar.gz",
                    "sha256": "abc123def456789"
                },
            ]
        }
    }


class TestVersionInfo:
    """Tests for VersionInfo dataclass."""

    def test_version_info_creation(self):
        """Test creating a VersionInfo object."""
        version = VersionInfo(
            version="0.1.20241223+62b9a1a85",
            installed_at="2024-12-23T10:00:00",
            backup_path="/home/user/.moon.backup.20241223_100000"
        )

        assert version.version == "0.1.20241223+62b9a1a85"
        assert version.installed_at == "2024-12-23T10:00:00"
        assert version.backup_path == "/home/user/.moon.backup.20241223_100000"

    def test_version_info_without_backup(self):
        """Test creating VersionInfo without backup path."""
        version = VersionInfo(
            version="0.1.20241223+62b9a1a85",
            installed_at="2024-12-23T10:00:00"
        )

        assert version.backup_path is None


class TestAvailableVersion:
    """Tests for AvailableVersion dataclass."""

    def test_available_version_creation(self):
        """Test creating an AvailableVersion object."""
        version = AvailableVersion(
            version="0.1.20241223+62b9a1a85",
            filename="moonbit-v0.1.20241223+62b9a1a85-linux-x64.tar.gz",
            sha256="e613706d44dea09c4089b137884fc64ce6b9ce0e43661778432eeaa8b6c6d519",
            last_modified="2024-12-23T10:00:00"
        )

        assert version.version == "0.1.20241223+62b9a1a85"
        assert version.filename.endswith(".tar.gz")
        assert len(version.sha256) == 64


class TestVersionManager:
    """Tests for VersionManager class."""

    def test_version_manager_init_creates_history_file(self, temp_config_dir):
        """Test that VersionManager creates history file on init."""
        manager = VersionManager()
        history_file = temp_config_dir / "version_history.json"

        assert history_file.exists()
        content = json.loads(history_file.read_text())
        assert "versions" in content
        assert content["versions"] == []

    def test_add_version(self, temp_config_dir):
        """Test adding a version to history."""
        manager = VersionManager()
        manager.add_version("0.1.20241223+62b9a1a85", Path("/backup/path"))

        history = manager.get_history()
        assert len(history) == 1
        assert history[0].version == "0.1.20241223+62b9a1a85"
        assert history[0].backup_path == "/backup/path"

    def test_add_version_without_backup(self, temp_config_dir):
        """Test adding a version without backup path."""
        manager = VersionManager()
        manager.add_version("0.1.20241223+62b9a1a85")

        history = manager.get_history()
        assert len(history) == 1
        assert history[0].backup_path is None

    def test_get_history(self, temp_config_dir):
        """Test getting version history."""
        manager = VersionManager()
        manager.add_version("0.1.20241223+v1")
        manager.add_version("0.1.20241224+v2")

        history = manager.get_history()
        assert len(history) == 2
        assert history[0].version == "0.1.20241223+v1"
        assert history[1].version == "0.1.20241224+v2"

    def test_get_previous_version(self, temp_config_dir):
        """Test getting previous version for rollback."""
        manager = VersionManager()
        manager.add_version("0.1.20241223+v1", Path("/backup1"))
        manager.add_version("0.1.20241224+v2", Path("/backup2"))

        previous = manager.get_previous_version()
        assert previous is not None
        assert previous.version == "0.1.20241223+v1"
        assert previous.backup_path == "/backup1"

    def test_get_previous_version_with_insufficient_history(self, temp_config_dir):
        """Test getting previous version when history is insufficient."""
        manager = VersionManager()
        manager.add_version("0.1.20241223+v1")

        previous = manager.get_previous_version()
        assert previous is None

    def test_get_previous_version_empty_history(self, temp_config_dir):
        """Test getting previous version with empty history."""
        manager = VersionManager()
        previous = manager.get_previous_version()
        assert previous is None


class TestFetchMoonbitBinariesIndex:
    """Tests for fetch_moonbit_binaries_index function."""

    @responses.activate
    def test_fetch_index_from_https(self, sample_index, monkeypatch):
        """Test fetching index from HTTPS URL."""
        # Mock config to return HTTPS URL
        mock_config = Mock()
        mock_config.mirror.index_url = "https://example.com/index.json"
        monkeypatch.setattr("moonbit_up.version.load_config", lambda: mock_config)

        # Mock HTTP response
        responses.add(
            responses.GET,
            "https://example.com/index.json",
            json=sample_index,
            status=200
        )

        index = fetch_moonbit_binaries_index()

        assert index is not None
        assert "linux-x64" in index
        assert len(index["linux-x64"]["releases"]) == 2

    def test_fetch_index_from_file(self, tmp_path, sample_index, monkeypatch):
        """Test fetching index from file:// URL."""
        # Create a local index file
        index_file = tmp_path / "index.json"
        index_file.write_text(json.dumps(sample_index))

        # Mock config to return file:// URL
        mock_config = Mock()
        mock_config.mirror.index_url = f"file://{index_file}"
        monkeypatch.setattr("moonbit_up.version.load_config", lambda: mock_config)

        index = fetch_moonbit_binaries_index()

        assert index is not None
        assert "linux-x64" in index
        assert len(index["linux-x64"]["releases"]) == 2

    def test_fetch_index_file_not_found(self, monkeypatch):
        """Test fetching index from non-existent file."""
        mock_config = Mock()
        mock_config.mirror.index_url = "file:///nonexistent/index.json"
        monkeypatch.setattr("moonbit_up.version.load_config", lambda: mock_config)

        index = fetch_moonbit_binaries_index()

        assert index is None

    @responses.activate
    def test_fetch_index_http_error(self, monkeypatch):
        """Test handling HTTP errors."""
        mock_config = Mock()
        mock_config.mirror.index_url = "https://example.com/index.json"
        monkeypatch.setattr("moonbit_up.version.load_config", lambda: mock_config)

        responses.add(
            responses.GET,
            "https://example.com/index.json",
            status=404
        )

        index = fetch_moonbit_binaries_index()

        assert index is None


class TestListAvailableVersions:
    """Tests for list_available_versions function."""

    def test_list_versions(self, sample_index, monkeypatch):
        """Test listing available versions."""
        monkeypatch.setattr(
            "moonbit_up.version.fetch_moonbit_binaries_index",
            lambda: sample_index
        )

        versions = list_available_versions()

        assert len(versions) == 2
        assert versions[0].version == "0.1.20241223+62b9a1a85"
        assert versions[1].version == "0.1.20241218+f4a066f5f"

    def test_list_versions_with_limit(self, sample_index, monkeypatch):
        """Test listing versions with limit."""
        monkeypatch.setattr(
            "moonbit_up.version.fetch_moonbit_binaries_index",
            lambda: sample_index
        )

        versions = list_available_versions(limit=1)

        assert len(versions) == 1
        assert versions[0].version == "0.1.20241223+62b9a1a85"

    def test_list_versions_empty_index(self, monkeypatch):
        """Test listing versions when index fetch fails."""
        monkeypatch.setattr(
            "moonbit_up.version.fetch_moonbit_binaries_index",
            lambda: None
        )

        versions = list_available_versions()

        assert versions == []

    def test_list_versions_preserves_metadata(self, sample_index, monkeypatch):
        """Test that version metadata is preserved."""
        monkeypatch.setattr(
            "moonbit_up.version.fetch_moonbit_binaries_index",
            lambda: sample_index
        )

        versions = list_available_versions()

        assert versions[0].filename == "moonbit-v0.1.20241223+62b9a1a85-linux-x64.tar.gz"
        assert versions[0].sha256 == "e613706d44dea09c4089b137884fc64ce6b9ce0e43661778432eeaa8b6c6d519"
        assert versions[0].last_modified == "2024-12-23T10:00:00"
