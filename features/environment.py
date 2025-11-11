"""Behave environment setup for integration tests."""

import tempfile
import shutil
from pathlib import Path


def before_all(context):
    """Set up test environment before all tests."""
    # Store original HOME
    import os
    context.original_home = os.environ.get("HOME")


def before_scenario(context, scenario):
    """Set up before each scenario."""
    # Create temporary directory for this scenario
    context.temp_dir = Path(tempfile.mkdtemp(prefix="moonbit-up-test-"))

    # Initialize variables
    context.config_dir = None
    context.mirror_dir = None
    context.last_command = None
    context.last_result = None
    context.last_output = ""
    context.last_returncode = None


def after_scenario(context, scenario):
    """Clean up after each scenario."""
    # Remove temporary directory
    if hasattr(context, 'temp_dir') and context.temp_dir.exists():
        shutil.rmtree(context.temp_dir, ignore_errors=True)


def after_all(context):
    """Clean up after all tests."""
    # Restore original HOME if it was changed
    if hasattr(context, 'original_home'):
        import os
        if context.original_home:
            os.environ["HOME"] = context.original_home
