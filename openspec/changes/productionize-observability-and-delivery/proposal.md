## Why

The system needs end-to-end diagnostics and reproducible delivery before it can be operated safely. Logging is fragmented, health semantics are shallow, deployment dependencies drift, and there is no complete CI/release/runbook loop.

## What Changes

- Centralize structured logging with correlation IDs, redaction, bounded payloads, metrics, and distinct liveness/readiness signals.
- Add stage metrics for crawl, extraction, LLM usage, jobs, indexing, retrieval, queues, errors, and resource consumption.
- Establish Windows/Linux CI, offline default checks, optional external suites, dependency/security scans, and artifact reporting.
- Harden and reproduce container builds, secret injection, non-root filesystem permissions, health checks, shutdown, Nginx, SBOM, and rollback.
- Correct README/architecture/API/MCP/runbook documentation and add a release/checklist process.

Non-goals: deploying publicly, purchasing monitoring infrastructure, deleting logs/data, enabling external tests by default, or guaranteeing a specific cloud provider.

Prerequisites: all preceding changes; it may begin earlier for logging and CI but final acceptance follows stable runtime, boundaries, jobs, artifacts, and retrieval.

## Capabilities

### New Capabilities
- `operational-observability`: Operators can correlate work end to end, measure health and budgets, and diagnose failures without exposing secrets.
- `reproducible-delivery`: CI, containers, releases, upgrades, rollback, and documentation provide a repeatable supported delivery path.

### Modified Capabilities

None.

## Impact

Affects logging setup, all runtime surfaces, health endpoints, CI configuration, Docker/Compose/Nginx, dependency locks, release metadata, README and operational documentation. Public deployment and external service provisioning remain manual decisions.
