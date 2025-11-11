# Testing Guide for moonbit-up

This document describes the testing strategy and how to run tests for moonbit-up.

## Testing Strategy

moonbit-up uses a multi-layered testing approach:

1. **Unit Tests** - Test individual modules and functions in isolation
2. **Integration Tests** - Test command-line interface and feature workflows using Gherkin/Behave

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_config.py            # Config module tests
│   ├── test_version.py           # Version management tests
│   └── test_mirror.py            # Mirror management tests
features/                          # Gherkin/Behave tests
├── environment.py                 # Behave test setup
├── configuration.feature          # Configuration scenarios
├── mirror_management.feature      # Mirror scenarios
├── version_listing.feature        # Version listing scenarios
└── steps/                         # Step definitions
    ├── common_steps.py
    ├── config_steps.py
    ├── mirror_steps.py
    └── version_steps.py
```

## Prerequisites

Install test dependencies:

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install moonbit-up with test dependencies
pip install -e ".[test]"
```

## Running Tests

### Run All Unit Tests

```bash
source .venv/bin/activate
pytest tests/unit/ -v
```

### Run Tests with Coverage

```bash
source .venv/bin/activate
pytest tests/unit/ --cov=moonbit_up --cov-report=html --cov-report=term
```

This generates:
- Terminal coverage summary
- HTML coverage report in `htmlcov/index.html`

### Run Specific Test Files

```bash
# Test only config module
pytest tests/unit/test_config.py -v

# Test only version module
pytest tests/unit/test_version.py -v

# Test only mirror module
pytest tests/unit/test_mirror.py -v
```

### Run Integration Tests (Behave)

```bash
source .venv/bin/activate
behave features/
```

Run specific features:

```bash
# Test only configuration features
behave features/configuration.feature

# Test only mirror management
behave features/mirror_management.feature

# Test only version listing
behave features/version_listing.feature
```

Run with specific tags:

```bash
# Run scenarios tagged with @smoke
behave --tags=@smoke

# Run all except @slow scenarios
behave --tags=-slow
```

## Test Coverage

Current test coverage:

- **Config Module**: 11 tests covering configuration loading, saving, and mirror settings
- **Version Module**: 18 tests covering version management, history tracking, and version fetching
- **Mirror Module**: 12 tests covering mirror creation, syncing, and information display
- **Integration Tests**: 15+ Gherkin scenarios covering end-to-end workflows

### Coverage Goals

- Maintain >80% code coverage for all modules
- All public APIs must have unit tests
- Critical paths must have integration tests

## Writing Tests

### Unit Test Example

```python
def test_load_config_reads_existing_file(temp_config_dir):
    """Test loading an existing config file."""
    config_file = temp_config_dir / "config.toml"
    config_content = """
[mirror]
index_url = "https://custom.com/index.json"
"""
    config_file.write_text(config_content)

    config = load_config()

    assert config.mirror.index_url == "https://custom.com/index.json"
```

### Integration Test Example (Gherkin)

```gherkin
Feature: Configuration Management
  Scenario: Set custom index URL
    When I run "moonbit-up config --index-url 'https://custom.com/index.json'"
    Then the command succeeds
    And the output contains "Index URL updated"
```

## Continuous Integration

moonbit-up tests can be integrated into CI/CD pipelines:

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[test]"

      - name: Run unit tests
        run: pytest tests/unit/ --cov=moonbit_up --cov-report=xml

      - name: Run integration tests
        run: behave features/

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Best Practices

1. **Isolation**: Each test should be independent and not rely on others
2. **Clarity**: Test names should clearly describe what they test
3. **Arrange-Act-Assert**: Structure tests with clear setup, action, and verification
4. **Mocking**: Use mocks for external dependencies (HTTP requests, file system)
5. **Fixtures**: Use pytest fixtures for common test setup
6. **Fast**: Unit tests should run quickly (<1 second each)

## Debugging Tests

### Run with verbose output:

```bash
pytest tests/unit/ -vv
```

### Run with print statements visible:

```bash
pytest tests/unit/ -s
```

### Run specific test:

```bash
pytest tests/unit/test_config.py::TestLoadConfig::test_load_config_reads_existing_file -v
```

### Debug with pdb:

```bash
pytest tests/unit/ --pdb
```

## Common Testing Patterns

### Mocking HTTP Requests

```python
import responses

@responses.activate
def test_fetch_index():
    responses.add(
        responses.GET,
        "https://example.com/index.json",
        json={"version": "1.0"},
        status=200
    )

    result = fetch_index()
    assert result["version"] == "1.0"
```

### Temporary Directories

```python
def test_with_temp_dir(tmp_path):
    """Use pytest's tmp_path fixture."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    assert test_file.read_text() == "content"
```

### Monkeypatching

```python
def test_with_mock_config(monkeypatch):
    """Mock a function return value."""
    monkeypatch.setattr(
        "moonbit_up.config.get_config_path",
        lambda: Path("/tmp/config.toml")
    )
    # Test code here
```

## Troubleshooting

### Tests fail with import errors

Ensure moonbit-up is installed in editable mode:

```bash
pip install -e .
```

### Behave tests can't find moonbit-up command

Ensure the command is in PATH or install with uv tool:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Coverage report not generating

Install coverage extras:

```bash
pip install pytest-cov
```

## Contributing Tests

When contributing new features:

1. Add unit tests for new functions/methods
2. Add integration tests for new CLI commands
3. Ensure all tests pass before submitting PR
4. Aim for >80% coverage of new code
5. Update this document if adding new test patterns
