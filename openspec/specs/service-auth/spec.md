# Service authentication

## Purpose

Define role-scoped credentials, secret-safe handling, and protected browser mutations for exposed service operations.

## Requirements

### Requirement: Role-scoped bearer authentication
Protected operations SHALL accept credentials only through the documented authorization header and SHALL distinguish read and administrative privileges.

#### Scenario: Read key on read endpoint
- **WHEN** a valid read credential calls a read operation
- **THEN** access is granted without administrative privileges

#### Scenario: Read key on administrative endpoint
- **WHEN** a read-only credential calls a mutating administrative operation
- **THEN** access is denied with a stable 403 response

### Requirement: Secret-safe processing
Credential comparisons SHALL be timing-safe for configured candidates, and credentials or identifying prefixes SHALL NOT appear in responses, logs, traces, or diagnostics.

#### Scenario: Authentication failure logging
- **WHEN** authentication fails
- **THEN** the audit event records outcome and correlation context without recording the supplied token

### Requirement: Protected browser mutations
Browser-facing state-changing operations SHALL require authorization plus an origin/CSRF policy appropriate to the deployment mode.

#### Scenario: Cross-origin mutation
- **WHEN** an untrusted origin attempts to clear or reload state
- **THEN** the operation is rejected without changing state
