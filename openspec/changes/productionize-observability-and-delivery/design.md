## Context

Operations span multiple entry points and long pipelines, but logging setup, health, CI, containers, and documentation are not a single supported product loop. This change integrates those concerns after core behavior stabilizes.

## Goals / Non-Goals

**Goals:** correlated redacted telemetry; meaningful health/budgets; reproducible CI/images/releases; secure runtime defaults; accurate runbooks/docs.

**Non-Goals:** selecting a hosted observability vendor, public deployment, or automatic destructive cleanup.

## Decisions

1. Configure logging once at composition and propagate correlation/job/document IDs through structured context. Export format remains replaceable.
2. Define low-cardinality metrics at stage boundaries and keep source URLs/titles out of labels.
3. Separate liveness from readiness and expose detailed diagnostics only under admin authorization.
4. CI has fast required offline jobs on Windows/Linux and explicit optional jobs for browser/network/model/container checks.
5. Build containers from the authoritative lock in stages, as non-root, with minimal runtime files and secrets injected externally.
6. Release artifacts include changelog, migrations, SBOM, smoke results, upgrade, and rollback instructions.

## Risks / Trade-offs

- [Telemetry adds overhead/cardinality] → benchmark and enforce bounded attributes/payloads.
- [Container hardening breaks writes] → declare writable mounts and test permissions as non-root.
- [Docs drift] → test commands/links and tie release checklist to documentation updates.

## Migration Plan

Centralize logging; add correlation and health; instrument stages; add CI; harden Docker/Compose/Nginx; add release/runbooks; perform local smoke/rollback exercises. Each layer is independently removable.

## Open Questions

- Which telemetry backend, if any, will consume the neutral metrics/log format?
