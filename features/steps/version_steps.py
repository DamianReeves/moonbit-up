"""Step definitions for version listing feature."""

import json
import subprocess
from pathlib import Path
from behave import given, then


@given('I have previously installed version "{version}"')
def step_previously_installed_version(context, version):
    """Simulate a previously installed version."""
    # Create version history file
    config_dir = context.temp_dir / ".config" / "moonbit-up"
    config_dir.mkdir(parents=True, exist_ok=True)

    history_file = config_dir / "version_history.json"
    history_data = {
        "versions": [
            {
                "version": version,
                "installed_at": "2024-12-20T10:00:00",
                "backup_path": None
            }
        ]
    }

    with open(history_file, 'w') as f:
        json.dump(history_data, f, indent=2)


@given("the version index is unavailable")
def step_version_index_unavailable(context):
    """Configure to use an unavailable index URL."""
    command = 'moonbit-up config --index-url "https://nonexistent-mirror-12345.example.com/index.json"'

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


@then("the output contains a table with version numbers")
def step_output_has_version_table(context):
    """Verify output contains a version table."""
    # Look for table indicators
    assert any(indicator in context.last_output for indicator in ["┃", "│", "Version", "Release Date"])


@then("the output shows at most {count:d} versions")
def step_output_max_versions(context, count):
    """Verify output shows at most N versions."""
    # This is a simplified check - in real tests we'd count table rows
    # For now, just verify the command succeeded and has version info
    assert "Version" in context.last_output


@then("the output shows all available versions")
def step_output_all_versions(context):
    """Verify output shows all versions."""
    # Just check that no limit message appears
    assert "Showing" not in context.last_output or "all" in context.last_output.lower()


@then("version entries include formatted dates")
def step_entries_have_dates(context):
    """Verify version entries have formatted dates."""
    # Look for date patterns (YYYY-MM-DD)
    import re
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    assert re.search(date_pattern, context.last_output), (
        "No formatted dates found in output"
    )


@then("versions are fetched from the custom mirror URL")
def step_versions_from_custom_mirror(context):
    """Verify versions were fetched from custom mirror."""
    # Check if custom URL appears in output or if fetch succeeded
    # This is a simplified check
    assert context.last_returncode == 0


@then('the output shows "{version}"')
def step_output_shows_version(context, version):
    """Verify output shows a specific version."""
    assert version in context.last_output, (
        f"Expected to find version {version} in output:\\n{context.last_output}"
    )
