"""Unit tests for mirror module."""

import json
import pytest
import responses
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from moonbit_up.mirror import MirrorManager
from moonbit_up.version import AvailableVersion


@pytest.fixture
def temp_mirror_dir(tmp_path):
    """Create a temporary mirror directory."""
    mirror_dir = tmp_path / "test-mirror"
    return mirror_dir


@pytest.fixture
def sample_versions():
    """Sample available versions."""
    return [
        AvailableVersion(
            version="0.1.20241223+62b9a1a85",
            filename="moonbit-v0.1.20241223+62b9a1a85-linux-x64.tar.gz",
            sha256="e613706d44dea09c4089b137884fc64ce6b9ce0e43661778432eeaa8b6c6d519",
            last_modified="2024-12-23T10:00:00"
        ),
        AvailableVersion(
            version="0.1.20241218+f4a066f5f",
            filename="moonbit-v0.1.20241218+f4a066f5f-linux-x64.tar.gz",
            sha256="abc123def456789",
            last_modified="2024-12-18T10:00:00"
        ),
    ]


class TestMirrorManagerInit:
    """Tests for MirrorManager initialization."""

    def test_init_sets_paths(self, temp_mirror_dir):
        """Test that MirrorManager sets correct paths."""
        manager = MirrorManager(temp_mirror_dir)

        assert manager.mirror_path == temp_mirror_dir
        assert manager.releases_dir == temp_mirror_dir / "releases"
        assert manager.index_file == temp_mirror_dir / "index.json"


class TestCreateMirror:
    """Tests for create_mirror method."""

    @responses.activate
    def test_create_mirror_latest_only(self, temp_mirror_dir, sample_versions, monkeypatch):
        """Test creating mirror with latest version only."""
        # Mock list_available_versions
        monkeypatch.setattr(
            "moonbit_up.mirror.list_available_versions",
            lambda: sample_versions
        )

        # Mock config
        mock_config = Mock()
        mock_config.mirror.download_base_url = "https://example.com/releases"
        monkeypatch.setattr("moonbit_up.mirror.load_config", lambda: mock_config)

        # Mock download
        responses.add(
            responses.GET,
            "https://example.com/releases/v0.1.20241223+62b9a1a85/moonbit-v0.1.20241223+62b9a1a85-linux-x64.tar.gz",
            body=b"fake tarball content",
            status=200
        )

        manager = MirrorManager(temp_mirror_dir)
        result = manager.create_mirror()

        assert result is True
        assert temp_mirror_dir.exists()
        assert manager.releases_dir.exists()
        assert manager.index_file.exists()

        # Check index content
        with open(manager.index_file) as f:
            index = json.load(f)

        assert "linux-x64" in index
        assert len(index["linux-x64"]["releases"]) == 1
        assert index["linux-x64"]["releases"][0]["version"] == "0.1.20241223+62b9a1a85"

    @responses.activate
    def test_create_mirror_all_versions(self, temp_mirror_dir, sample_versions, monkeypatch):
        """Test creating mirror with all versions."""
        monkeypatch.setattr(
            "moonbit_up.mirror.list_available_versions",
            lambda: sample_versions
        )

        mock_config = Mock()
        mock_config.mirror.download_base_url = "https://example.com/releases"
        monkeypatch.setattr("moonbit_up.mirror.load_config", lambda: mock_config)

        # Mock both downloads
        for ver in sample_versions:
            responses.add(
                responses.GET,
                f"https://example.com/releases/v{ver.version}/{ver.filename}",
                body=b"fake tarball content",
                status=200
            )

        manager = MirrorManager(temp_mirror_dir)
        result = manager.create_mirror(all_versions=True)

        assert result is True

        # Check index has all versions
        with open(manager.index_file) as f:
            index = json.load(f)

        assert len(index["linux-x64"]["releases"]) == 2

    @responses.activate
    def test_create_mirror_specific_versions(self, temp_mirror_dir, sample_versions, monkeypatch):
        """Test creating mirror with specific versions."""
        monkeypatch.setattr(
            "moonbit_up.mirror.list_available_versions",
            lambda: sample_versions
        )

        mock_config = Mock()
        mock_config.mirror.download_base_url = "https://example.com/releases"
        monkeypatch.setattr("moonbit_up.mirror.load_config", lambda: mock_config)

        # Mock download for specified version
        responses.add(
            responses.GET,
            "https://example.com/releases/v0.1.20241218+f4a066f5f/moonbit-v0.1.20241218+f4a066f5f-linux-x64.tar.gz",
            body=b"fake tarball content",
            status=200
        )

        manager = MirrorManager(temp_mirror_dir)
        result = manager.create_mirror(versions=["0.1.20241218+f4a066f5f"])

        assert result is True

        with open(manager.index_file) as f:
            index = json.load(f)

        assert len(index["linux-x64"]["releases"]) == 1
        assert index["linux-x64"]["releases"][0]["version"] == "0.1.20241218+f4a066f5f"

    def test_create_mirror_no_versions_available(self, temp_mirror_dir, monkeypatch):
        """Test creating mirror when no versions are available."""
        monkeypatch.setattr(
            "moonbit_up.mirror.list_available_versions",
            lambda: []
        )

        manager = MirrorManager(temp_mirror_dir)
        result = manager.create_mirror()

        assert result is False

    @responses.activate
    def test_create_mirror_skips_existing(self, temp_mirror_dir, sample_versions, monkeypatch):
        """Test that create_mirror skips already downloaded versions."""
        monkeypatch.setattr(
            "moonbit_up.mirror.list_available_versions",
            lambda: sample_versions
        )

        mock_config = Mock()
        mock_config.mirror.download_base_url = "https://example.com/releases"
        monkeypatch.setattr("moonbit_up.mirror.load_config", lambda: mock_config)

        manager = MirrorManager(temp_mirror_dir)

        # Create existing version file
        version_dir = manager.releases_dir / f"v{sample_versions[0].version}"
        version_dir.mkdir(parents=True)
        binary_path = version_dir / sample_versions[0].filename
        binary_path.write_bytes(b"existing content")

        # Should not make HTTP request for existing file
        result = manager.create_mirror()

        # Check that existing file wasn't overwritten
        assert binary_path.read_bytes() == b"existing content"


class TestSyncMirror:
    """Tests for sync_mirror method."""

    def test_sync_mirror_not_initialized(self, temp_mirror_dir):
        """Test syncing mirror that doesn't exist."""
        manager = MirrorManager(temp_mirror_dir)
        result = manager.sync_mirror()

        assert result is False

    @responses.activate
    def test_sync_mirror_no_new_versions(self, temp_mirror_dir, sample_versions, monkeypatch):
        """Test syncing mirror when no new versions available."""
        # Create initial mirror
        manager = MirrorManager(temp_mirror_dir)
        manager.mirror_path.mkdir(parents=True)
        manager.releases_dir.mkdir(parents=True)

        # Create index with all current versions
        index_data = {
            "linux-x64": {
                "last_modified": "2024-12-23T10:00:00",
                "releases": [
                    {"version": v.version, "name": v.filename, "sha256": v.sha256}
                    for v in sample_versions
                ]
            }
        }
        with open(manager.index_file, 'w') as f:
            json.dump(index_data, f)

        # Mock upstream to have same versions
        monkeypatch.setattr(
            "moonbit_up.mirror.list_available_versions",
            lambda: sample_versions
        )

        result = manager.sync_mirror()

        assert result is True

    @responses.activate
    def test_sync_mirror_with_new_versions(self, temp_mirror_dir, sample_versions, monkeypatch):
        """Test syncing mirror with new upstream versions."""
        manager = MirrorManager(temp_mirror_dir)
        manager.mirror_path.mkdir(parents=True)
        manager.releases_dir.mkdir(parents=True)

        # Create index with only old version
        index_data = {
            "linux-x64": {
                "last_modified": "2024-12-18T10:00:00",
                "releases": [
                    {
                        "version": sample_versions[1].version,
                        "name": sample_versions[1].filename,
                        "sha256": sample_versions[1].sha256
                    }
                ]
            }
        }
        with open(manager.index_file, 'w') as f:
            json.dump(index_data, f)

        # Mock upstream to have new version
        monkeypatch.setattr(
            "moonbit_up.mirror.list_available_versions",
            lambda: sample_versions
        )

        mock_config = Mock()
        mock_config.mirror.download_base_url = "https://example.com/releases"
        monkeypatch.setattr("moonbit_up.mirror.load_config", lambda: mock_config)

        # Mock download for new version
        responses.add(
            responses.GET,
            f"https://example.com/releases/v{sample_versions[0].version}/{sample_versions[0].filename}",
            body=b"new version content",
            status=200
        )

        result = manager.sync_mirror()

        assert result is True

        # Check that index was updated
        with open(manager.index_file) as f:
            index = json.load(f)

        assert len(index["linux-x64"]["releases"]) == 2


class TestInfo:
    """Tests for info method."""

    def test_info_mirror_not_exists(self, temp_mirror_dir, capsys):
        """Test info when mirror doesn't exist."""
        manager = MirrorManager(temp_mirror_dir)
        manager.info()

        captured = capsys.readouterr()
        assert "not set up" in captured.out

    def test_info_mirror_exists(self, temp_mirror_dir, sample_versions, capsys):
        """Test info when mirror exists."""
        manager = MirrorManager(temp_mirror_dir)
        manager.mirror_path.mkdir(parents=True)
        manager.releases_dir.mkdir(parents=True)

        # Create index
        index_data = {
            "linux-x64": {
                "last_modified": "2024-12-23T10:00:00",
                "releases": [
                    {"version": v.version, "name": v.filename, "sha256": v.sha256}
                    for v in sample_versions
                ]
            }
        }
        with open(manager.index_file, 'w') as f:
            json.dump(index_data, f)

        # Create a dummy release file for disk usage calculation
        version_dir = manager.releases_dir / f"v{sample_versions[0].version}"
        version_dir.mkdir(parents=True)
        (version_dir / sample_versions[0].filename).write_bytes(b"x" * 1024 * 1024)  # 1MB

        manager.info()

        captured = capsys.readouterr()
        assert "Mirror Information" in captured.out
        assert "Versions:" in captured.out
        assert "2" in captured.out  # Should show 2 versions


class TestCreateIndex:
    """Tests for _create_index method."""

    def test_create_index(self, temp_mirror_dir, sample_versions):
        """Test creating index file."""
        manager = MirrorManager(temp_mirror_dir)
        manager.mirror_path.mkdir(parents=True)

        manager._create_index(sample_versions)

        assert manager.index_file.exists()

        with open(manager.index_file) as f:
            index = json.load(f)

        assert "linux-x64" in index
        assert "last_modified" in index["linux-x64"]
        assert "releases" in index["linux-x64"]
        assert len(index["linux-x64"]["releases"]) == 2

        # Check version data
        releases = index["linux-x64"]["releases"]
        assert releases[0]["version"] == sample_versions[0].version
        assert releases[0]["name"] == sample_versions[0].filename
        assert releases[0]["sha256"] == sample_versions[0].sha256
