"""Common step definitions for Behave tests."""

import os
import json
import shutil
import subprocess
from pathlib import Path
from behave import given, when, then, use_step_matcher


use_step_matcher("parse")


@given("a clean configuration directory")
def step_clean_config_dir(context):
    """Create a clean temporary config directory."""
    context.config_dir = context.temp_dir / ".config" / "moonbit-up"
    context.config_dir.mkdir(parents=True, exist_ok=True)

    # Set environment to use temp config
    os.environ["HOME"] = str(context.temp_dir)


@given("a temporary mirror directory")
def step_temp_mirror_dir(context):
    """Create a temporary mirror directory."""
    context.mirror_dir = context.temp_dir / "test-mirror"
    context.mirror_dir.mkdir(parents=True, exist_ok=True)


@when('I run "{command}"')
def step_run_command(context, command):
    """Run a moonbit-up command."""
    # Replace placeholders
    command = command.replace("{mirror_dir}", str(context.mirror_dir))

    # Set environment
    env = os.environ.copy()
    env["HOME"] = str(context.temp_dir)
    env["PATH"] = f"{Path.home()}/.local/bin:{env.get('PATH', '')}"

    # Run command
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=60
    )

    context.last_command = command
    context.last_result = result
    context.last_output = result.stdout + result.stderr
    context.last_returncode = result.returncode


@then("the command succeeds")
def step_command_succeeds(context):
    """Verify the command succeeded."""
    assert context.last_returncode == 0, (
        f"Command failed with exit code {context.last_returncode}\\n"
        f"Command: {context.last_command}\\n"
        f"Output: {context.last_output}"
    )


@then("the command fails")
def step_command_fails(context):
    """Verify the command failed."""
    assert context.last_returncode != 0, (
        f"Command succeeded but was expected to fail\\n"
        f"Command: {context.last_command}\\n"
        f"Output: {context.last_output}"
    )


@then('the output contains "{text}"')
def step_output_contains(context, text):
    """Verify output contains specific text."""
    assert text in context.last_output, (
        f"Expected output to contain '{text}'\\n"
        f"Actual output: {context.last_output}"
    )


@then('the output does not contain "{text}"')
def step_output_not_contains(context, text):
    """Verify output does not contain specific text."""
    assert text not in context.last_output, (
        f"Expected output to NOT contain '{text}'\\n"
        f"Actual output: {context.last_output}"
    )


@then('a directory exists at "{path}"')
def step_directory_exists(context, path):
    """Verify a directory exists."""
    path = path.replace("{mirror_dir}", str(context.mirror_dir))
    full_path = Path(path)
    assert full_path.exists() and full_path.is_dir(), (
        f"Expected directory to exist at {full_path}"
    )


@then('a file exists at "{path}"')
def step_file_exists(context, path):
    """Verify a file exists."""
    path = path.replace("{mirror_dir}", str(context.mirror_dir))
    full_path = Path(path)
    assert full_path.exists() and full_path.is_file(), (
        f"Expected file to exist at {full_path}"
    )


def get_index_file(context):
    """Get the mirror index file."""
    index_file = context.mirror_dir / "index.json"
    if not index_file.exists():
        raise FileNotFoundError(f"Index file not found at {index_file}")

    with open(index_file) as f:
        return json.load(f)


@then("the index file contains {count:d} version")
@then("the index file contains {count:d} versions")
def step_index_contains_versions(context, count):
    """Verify index contains specific number of versions."""
    index = get_index_file(context)
    actual_count = len(index["linux-x64"]["releases"])
    assert actual_count == count, (
        f"Expected {count} versions but found {actual_count}"
    )


@then("the index file contains multiple versions")
def step_index_contains_multiple(context):
    """Verify index contains more than one version."""
    index = get_index_file(context)
    count = len(index["linux-x64"]["releases"])
    assert count > 1, f"Expected multiple versions but found {count}"


@then('the index file contains version "{version}"')
def step_index_contains_version(context, version):
    """Verify index contains a specific version."""
    index = get_index_file(context)
    versions = [r["version"] for r in index["linux-x64"]["releases"]]
    assert version in versions, (
        f"Expected version {version} not found in index.\\n"
        f"Available versions: {versions}"
    )
