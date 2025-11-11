Feature: Configuration Management
  As a moonbit-up user
  I want to manage my configuration settings
  So that I can customize mirror URLs and installation behavior

  Background:
    Given a clean configuration directory

  Scenario: View default configuration
    When I run "moonbit-up config"
    Then the command succeeds
    And the output contains "Configuration"
    And the output contains "index_url"
    And the output contains "download_base_url"
    And the output contains "backup_enabled"

  Scenario: Set custom index URL
    When I run "moonbit-up config --index-url 'https://custom-mirror.com/index.json'"
    Then the command succeeds
    And the output contains "Index URL updated"
    When I run "moonbit-up config"
    Then the output contains "https://custom-mirror.com/index.json"

  Scenario: Set custom download URL
    When I run "moonbit-up config --download-url 'https://custom-mirror.com/releases'"
    Then the command succeeds
    And the output contains "Download URL updated"
    When I run "moonbit-up config"
    Then the output contains "https://custom-mirror.com/releases"

  Scenario: Set both mirror URLs
    When I run "moonbit-up config --index-url 'https://mirror.com/index.json' --download-url 'https://mirror.com/releases'"
    Then the command succeeds
    And the output contains "Index URL updated"
    And the output contains "Download URL updated"

  Scenario: Reset configuration to defaults
    Given I have set a custom index URL to "https://custom.com/index.json"
    When I run "moonbit-up config --reset"
    Then the command succeeds
    And the output contains "reset to defaults"
    When I run "moonbit-up config"
    Then the output does not contain "custom.com"

  Scenario: Configuration persists across commands
    When I run "moonbit-up config --index-url 'https://persistent.com/index.json'"
    Then the command succeeds
    When I run "moonbit-up config"
    Then the output contains "https://persistent.com/index.json"
