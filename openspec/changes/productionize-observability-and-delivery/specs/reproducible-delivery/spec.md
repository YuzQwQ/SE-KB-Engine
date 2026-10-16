## ADDED Requirements

### Requirement: Cross-platform required CI
Required CI SHALL run source/encoding, compile, lint, type, and deterministic offline tests on the supported Windows and Linux/Python matrix.

#### Scenario: Pull request validation
- **WHEN** a proposed change violates a required gate
- **THEN** CI fails with the constituent command output and no external secret is required

### Requirement: Reproducible hardened image
The production image SHALL use the authoritative locked dependencies, a supported Python base, minimal runtime content, non-root execution, declared writable paths, and no embedded secrets.

#### Scenario: Container smoke test
- **WHEN** the image starts with temporary data and injected test credentials
- **THEN** health, authorization, degraded behavior, and graceful shutdown pass as non-root

### Requirement: Controlled release and rollback
Each release SHALL identify version, changes, dependency/security evidence, data/index migrations, smoke results, upgrade steps, and rollback steps.

#### Scenario: Migration-bearing release
- **WHEN** a release changes artifact or index format
- **THEN** deployment is blocked until backup, dry-run, validation, and rollback instructions exist

### Requirement: Accurate operator documentation
Documentation SHALL distinguish MCP, REST, Web, and script entry points and accurately state setup, configuration, data locations, network/cost side effects, troubleshooting, and supported capabilities.

#### Scenario: Documentation verification
- **WHEN** documented offline setup and smoke commands run in a clean environment
- **THEN** they complete as described or the documentation check fails
