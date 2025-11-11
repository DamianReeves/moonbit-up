"""Step definitions for configuration feature."""

import subprocess
from pathlib import Path
from behave import given


@given('I have set a custom index URL to "{url}"')
def step_set_custom_index_url(context, url):
    """Set a custom index URL in configuration."""
    # Run the config command
    command = f'moonbit-up config --index-url "{url}"'

    env = {
        "HOME": str(context.temp_dir),
        "PATH": f"{Path.home()}/.local/bin:{Path.home()}/bin:/usr/local/bin:/usr/bin:/bin"
    }

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )

    assert result.returncode == 0, f"Failed to set custom URL: {result.stderr}"
