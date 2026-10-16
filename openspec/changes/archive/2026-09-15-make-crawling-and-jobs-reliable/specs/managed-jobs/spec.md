## ADDED Requirements

### Requirement: Isolated job identity and state
Every long-running operation SHALL have a stable job ID, immutable submitted parameters, timestamps, progress, result reference, and one of queued, running, succeeded, failed, cancelled, or interrupted states.

#### Scenario: Concurrent jobs
- **WHEN** two jobs run concurrently
- **THEN** their progress, logs, cancellation, errors, and results remain isolated by job ID

### Requirement: Valid job transitions
Job state changes SHALL follow a validated transition table and SHALL be safe under concurrent observation and cancellation.

#### Scenario: Late success after cancellation
- **WHEN** a worker reports success after cancellation was accepted
- **THEN** the store preserves the cancelled terminal state and records the late event diagnostically

### Requirement: Cooperative cancellation
Cancellation SHALL propagate to queued work, network operations, browser work, model calls when supported, and artifact publication checkpoints.

#### Scenario: Cancel queued job
- **WHEN** a queued job is cancelled
- **THEN** it never starts and reports cancelled with no output artifact

### Requirement: Restart semantics
Jobs left non-terminal by an unclean process exit SHALL be identified as interrupted or resumed according to an explicit policy.

#### Scenario: Service restart
- **WHEN** the service starts with previously running jobs
- **THEN** no job remains falsely reported as running without an active worker
