# Offline quality gates

## Purpose

Define the deterministic, offline-by-default validation contract for repository changes.

## Requirements

### Requirement: Offline tests by default
The default test command SHALL run deterministic offline tests and SHALL exclude network, paid LLM, browser, Tor, Docker, and slow suites unless explicitly selected.

#### Scenario: Default test run
- **WHEN** a contributor runs the documented default test command without credentials
- **THEN** the suite completes without external connections or writes outside temporary locations

### Requirement: Isolated test resources
Tests SHALL isolate environment variables, time, randomness, filesystem paths, HTTP/model clients, and application state when those resources affect outcomes.

#### Scenario: Test cleanup
- **WHEN** a test mutates a fixture environment or temporary datastore
- **THEN** the next test observes the original process environment and no production data change

### Requirement: Composable quality gate
The project SHALL provide one documented command that runs encoding/compile checks, lint, type checks, and the fast offline suite while preserving individual tool output.

#### Scenario: Quality failure
- **WHEN** one constituent check fails
- **THEN** the aggregate command exits non-zero and identifies the failing check

### Requirement: Baseline without weakened validation
Quality failures SHALL NOT be resolved by deleting tests, reducing assertions, silently swallowing failures, or adding broad permanent exclusions.

#### Scenario: Existing debt
- **WHEN** a category cannot be fixed safely in the current batch
- **THEN** it remains visible as scoped debt with a rationale and follow-up task
