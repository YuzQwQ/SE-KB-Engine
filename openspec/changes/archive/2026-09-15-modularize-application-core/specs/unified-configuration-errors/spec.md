## ADDED Requirements

### Requirement: Typed configuration precedence
Settings SHALL validate and resolve defaults, configuration files, environment variables, and explicit arguments using one documented precedence order.

#### Scenario: Invalid setting
- **WHEN** startup receives an invalid timeout, path, URL, or enum
- **THEN** validation fails with the setting name and remediation but without its sensitive value

### Requirement: Stable path resolution
Project, configuration, data, cache, and output paths SHALL resolve independently of the caller's current working directory.

#### Scenario: Start from another directory
- **WHEN** a supported module entry point starts outside the repository root
- **THEN** it locates configured resources using resolved roots rather than relative process paths

### Requirement: Typed failure taxonomy
Application failures SHALL be categorized at least as configuration, authorization, policy, network, parsing, extraction, validation, storage, retrieval, cancellation, and internal errors.

#### Scenario: Retry decision
- **WHEN** an adapter receives an application error
- **THEN** it can map the safe public code and determine retryability without matching message substrings
