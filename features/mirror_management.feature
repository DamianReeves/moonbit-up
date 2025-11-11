Feature: Mirror Management
  As a moonbit-up user
  I want to create and manage local mirrors
  So that I can use moonbit-up offline or with faster local downloads

  Background:
    Given a temporary mirror directory

  Scenario: Create mirror with latest version only
    When I run "moonbit-up mirror create --path {mirror_dir}"
    Then the command succeeds
    And the output contains "Mirror created successfully"
    And a directory exists at "{mirror_dir}/releases"
    And a file exists at "{mirror_dir}/index.json"
    And the index file contains 1 version

  Scenario: Create mirror with all versions
    When I run "moonbit-up mirror create --path {mirror_dir} --all"
    Then the command succeeds
    And the output contains "Mirroring all"
    And the index file contains multiple versions

  Scenario: Create mirror with specific version
    When I run "moonbit-up mirror create --path {mirror_dir} --version '0.1.20241218+f4a066f5f'"
    Then the command succeeds
    And the index file contains version "0.1.20241218+f4a066f5f"

  Scenario: View mirror information
    Given a mirror exists with 2 versions
    When I run "moonbit-up mirror info --path {mirror_dir}"
    Then the command succeeds
    And the output contains "Mirror Information"
    And the output contains "Versions: 2"
    And the output contains "Disk Usage"

  Scenario: View info for non-existent mirror
    When I run "moonbit-up mirror info --path {mirror_dir}"
    Then the command succeeds
    And the output contains "not set up"

  Scenario: Sync mirror with upstream
    Given a mirror exists with 1 version
    When new versions are available upstream
    And I run "moonbit-up mirror sync --path {mirror_dir}"
    Then the command succeeds
    And the output contains "new versions"
    And the index file contains more versions than before

  Scenario: Sync mirror with no new versions
    Given a mirror exists with latest versions
    When I run "moonbit-up mirror sync --path {mirror_dir}"
    Then the command succeeds
    And the output contains "up to date"

  Scenario: Sync non-existent mirror fails
    When I run "moonbit-up mirror sync --path {mirror_dir}"
    Then the command fails
    And the output contains "not initialized"

  Scenario: Use file:// URLs for local mirror
    Given a mirror exists with 1 version
    When I configure moonbit-up to use file:// URLs for the mirror
    And I run "moonbit-up list"
    Then the command succeeds
    And the output lists versions from the local mirror

  Scenario: List versions from local mirror
    Given a mirror exists with 2 versions
    And moonbit-up is configured to use the local mirror
    When I run "moonbit-up list"
    Then the command succeeds
    And the output contains 2 versions

  Scenario: Create mirror skips existing files
    Given a mirror exists with 1 version
    And the mirror binary file has a timestamp
    When I run "moonbit-up mirror create --path {mirror_dir}"
    Then the command succeeds
    And the output contains "already exists"
    And the binary file timestamp is unchanged
