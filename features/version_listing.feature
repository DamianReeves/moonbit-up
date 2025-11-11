Feature: Version Listing
  As a moonbit-up user
  I want to list available MoonBit versions
  So that I can choose which version to install

  Scenario: List recent versions
    When I run "moonbit-up list"
    Then the command succeeds
    And the output contains "Available MoonBit Versions"
    And the output contains a table with version numbers
    And the output shows at most 20 versions

  Scenario: List all available versions
    When I run "moonbit-up list --all"
    Then the command succeeds
    And the output contains "Available MoonBit Versions"
    And the output shows all available versions

  Scenario: List versions shows release dates
    When I run "moonbit-up list"
    Then the command succeeds
    And the output contains "Release Date"
    And version entries include formatted dates

  Scenario: List versions handles network failure gracefully
    Given the version index is unavailable
    When I run "moonbit-up list"
    Then the command succeeds
    And the output contains "Could not fetch available versions"
    And the output contains "Use 'latest' to install"

  Scenario: List versions from custom mirror
    Given moonbit-up is configured with a custom mirror
    When I run "moonbit-up list"
    Then the command succeeds
    And versions are fetched from the custom mirror URL

  Scenario: List shows previously installed versions
    Given I have previously installed version "0.1.20241223+62b9a1a85"
    When I run "moonbit-up list"
    Then the command succeeds
    And the output contains "Previously Installed Versions"
    And the output shows "0.1.20241223+62b9a1a85"
