import os
import stat
import tarfile
import tempfile
from pathlib import Path

import pytest
import responses

from moonbit_up.version import get_latest_for_channel
from moonbit_up import version as version_module
from moonbit_up.utils import candidate_asset_names_for_triple, detect_target_triple, probe_first_existing_asset
from moonbit_up.installer import MoonBitInstaller


@pytest.fixture
def fake_dist_index():
    return {
        "version": 3,
        "channels": [
            {"name": "latest", "version": "0.6.31+b5b06ff93"},
            {"name": "nightly", "version": "0.6.31+e3a45ea58", "date": "2025-11-13"},
        ],
    }


def test_get_latest_for_channel_nightly(monkeypatch, fake_dist_index):
    monkeypatch.setattr(version_module, "fetch_moonup_dist_index", lambda: fake_dist_index)
    latest = get_latest_for_channel("nightly")
    assert latest is not None
    version, date = latest
    assert version == "0.6.31+e3a45ea58"
    assert date == "2025-11-13"


def test_candidate_asset_names_include_nightly_pattern():
    triple = "x86_64-unknown-linux"
    date = "2025-11-13"
    names = candidate_asset_names_for_triple(triple, date=date)
    assert any(name.startswith(f"moonbit-nightly-{date}-{triple}") for name in names)
    # Ensure fallback stable pattern also included
    assert any(name.startswith(f"moonbit-{triple}") for name in names)


@responses.activate
def test_probe_first_existing_asset_redirect_and_success():
    base = "https://github.com/chawyehsu/moonbit-dist-nightly/releases/download"
    tag = "nightly-2025-11-13"
    triple = "x86_64-unknown-linux"
    date = "2025-11-13"
    candidates = candidate_asset_names_for_triple(triple, date=date)
    target_asset = candidates[0]
    url = f"{base}/{tag}/{target_asset}"

    responses.add(responses.HEAD, url, status=200)  # Simulate found asset
    resolved = probe_first_existing_asset(base, tag, candidates)
    assert resolved == url


def create_minimal_tar_with_bin(tmp_path: Path) -> Path:
    tar_path = tmp_path / "toolchain.tar.gz"
    bin_dir = tmp_path / "build" / "bin"
    bin_dir.mkdir(parents=True)
    moon_file = bin_dir / "moon"
    moon_file.write_text("#!/bin/sh\necho moon\n")
    # Remove execute permission intentionally
    moon_file.chmod(0o644)
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(bin_dir, arcname="bin")
    return tar_path


def test_extract_toolchain_sets_executable_bits(tmp_path, monkeypatch):
    # Use temp moon_home to avoid interfering with real installation
    installer = MoonBitInstaller()
    installer.moon_home = tmp_path / "moon_home"
    installer.moon_home.mkdir(parents=True, exist_ok=True)

    tar_path = create_minimal_tar_with_bin(tmp_path)
    ok = installer.extract_toolchain(tar_path, installer.moon_home)
    assert ok
    moon = installer.moon_home / "bin" / "moon"
    assert moon.exists()
    mode = moon.stat().st_mode
    assert mode & stat.S_IXUSR, "moon binary should be executable by user after extraction"


def test_detect_target_triple_linux_arm64_forces_x86_64(monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "aarch64")
    triple = detect_target_triple()
    assert triple == "x86_64-unknown-linux"
