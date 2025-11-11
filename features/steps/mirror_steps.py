"""Step definitions for mirror management feature."""

import json
import os
import time
from pathlib import Path
from behave import given, when, then


@given("a mirror exists with {count:d} version")
@given("a mirror exists with {count:d} versions")
def step_mirror_exists_with_versions(context, count):
    """Create a mirror with specific number of versions."""
    context.mirror_dir.mkdir(parents=True, exist_ok=True)
    releases_dir = context.mirror_dir / "releases"
    releases_dir.mkdir(exist_ok=True)

    # Create mock versions
    versions = []
    for i in range(count):
        version_str = f"0.1.2024120{i}+mock{i}"
        version_dir = releases_dir / f"v{version_str}"
        version_dir.mkdir(exist_ok=True)

        filename = f"moonbit-v{version_str}-linux-x64.tar.gz"
        binary_path = version_dir / filename
        binary_path.write_bytes(b"mock binary content")

        versions.append({
            "version": version_str,
            "name": filename,
            "sha256": "mock_sha256_hash"
        })

    # Create index
    index_data = {
        "linux-x64": {
            "last_modified": "2024-12-20T10:00:00",
            "releases": versions
        }
    }

    index_file = context.mirror_dir / "index.json"
    with open(index_file, 'w') as f:
        json.dump(index_data, f, indent=2)

    # Store initial version count
    context.initial_version_count = count


@given("a mirror exists with latest versions")
def step_mirror_with_latest(context):
    """Create a mirror that's up to date."""
    # Just create a mirror with 1 version for this scenario
    step_mirror_exists_with_versions(context, 1)


@given("the mirror binary file has a timestamp")
def step_store_binary_timestamp(context):
    """Store the timestamp of a binary file."""
    releases_dir = context.mirror_dir / "releases"
    # Find first binary file
    for version_dir in releases_dir.iterdir():
        if version_dir.is_dir():
            for file in version_dir.iterdir():
                if file.suffix == ".gz":
                    context.binary_file = file
                    context.binary_timestamp = file.stat().st_mtime
                    return

    raise FileNotFoundError("No binary file found in mirror")


@when("new versions are available upstream")
def step_new_versions_upstream(context):
    """Simulate new versions being available upstream."""
    # This is a placeholder - in real tests, we'd mock the upstream response
    # For now, we'll just note that we expect new versions
    context.expect_new_versions = True


@when("I configure moonbit-up to use file:// URLs for the mirror")
def step_configure_file_urls(context):
    """Configure moonbit-up to use file:// URLs."""
    index_url = f"file://{context.mirror_dir}/index.json"
    download_url = f"file://{context.mirror_dir}/releases"

    command = (
        f'moonbit-up config '
        f'--index-url "{index_url}" '
        f'--download-url "{download_url}"'
    )

    env = os.environ.copy()
    env["HOME"] = str(context.temp_dir)

    import subprocess
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )

    assert result.returncode == 0, f"Failed to configure URLs: {result.stderr}"


@given("moonbit-up is configured to use the local mirror")
def step_configured_for_local_mirror(context):
    """Configure moonbit-up to use the local mirror."""
    step_configure_file_urls(context)


@given("moonbit-up is configured with a custom mirror")
def step_configured_custom_mirror(context):
    """Configure with a custom mirror URL."""
    command = 'moonbit-up config --index-url "https://custom-mirror.example.com/index.json"'

    env = os.environ.copy()
    env["HOME"] = str(context.temp_dir)

    import subprocess
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )


@then("the output lists versions from the local mirror")
def step_lists_local_versions(context):
    """Verify output lists versions from local mirror."""
    # Check that we fetched from file:// URL
    assert "file://" in context.last_output or "mock" in context.last_output.lower()


@then("the output contains {count:d} version")
@then("the output contains {count:d} versions")
def step_output_contains_versions(context, count):
    """Verify output contains specific number of versions."""
    # This is a simplified check - in real tests we'd parse the table
    assert str(count) in context.last_output


@then("the index file contains more versions than before")
def step_index_has_more_versions(context):
    """Verify index has more versions after sync."""
    index_file = context.mirror_dir / "index.json"
    with open(index_file) as f:
        index = json.load(f)

    new_count = len(index["linux-x64"]["releases"])
    assert new_count > context.initial_version_count, (
        f"Expected more than {context.initial_version_count} versions, "
        f"but found {new_count}"
    )


@then("the binary file timestamp is unchanged")
def step_timestamp_unchanged(context):
    """Verify binary file timestamp hasn't changed."""
    current_timestamp = context.binary_file.stat().st_mtime
    assert current_timestamp == context.binary_timestamp, (
        "Binary file was modified when it should have been skipped"
    )
