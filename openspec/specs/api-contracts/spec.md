# API contracts

## Purpose

Define validated inputs and stable success, failure, and degraded-mode behavior at REST, Web, and MCP boundaries.

## Requirements

### Requirement: Validated external parameters
REST, Web, and MCP adapters SHALL validate required fields, types, lengths, enums, numeric ranges, and path components before invoking application services.

#### Scenario: Invalid top-k
- **WHEN** a client supplies a negative, non-integral, or excessive retrieval count
- **THEN** the adapter returns a field-specific client error and performs no retrieval

### Requirement: Stable error envelope
Public service errors SHALL contain a stable code, safe message, and correlation identifier without internal paths, stack traces, credentials, or upstream response bodies.

#### Scenario: Internal exception
- **WHEN** an unexpected exception occurs
- **THEN** the client receives a generic 500-class envelope and operators retain a sanitized correlated diagnostic

### Requirement: Explicit degraded state
Unavailable optional subsystems SHALL produce a documented degraded health/readiness result and dependent operations SHALL return a stable unavailable error.

#### Scenario: Empty vector service
- **WHEN** the retriever cannot initialize
- **THEN** liveness remains responsive, readiness identifies the unavailable capability, and search returns 503
