"""Pytest configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def mock_console(monkeypatch):
    """Mock the Rich console to capture output."""
    from io import StringIO
    from rich.console import Console

    output = StringIO()
    console = Console(file=output, force_terminal=False)

    # Monkeypatch all console instances
    monkeypatch.setattr("moonbit_up.config.console", console)
    monkeypatch.setattr("moonbit_up.version.console", console)
    monkeypatch.setattr("moonbit_up.mirror.console", console)
    monkeypatch.setattr("moonbit_up.installer.console", console)

    return output
