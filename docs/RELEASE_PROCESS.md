# Release process

The release version comes only from `pyproject.toml`. A tag must be exactly `v<version>`. Update `CHANGELOG.md` and do not tag a dirty or unreviewed tree.

For every release:

1. Freeze scope and compatibility; identify artifact/index/config/API/MCP changes.
2. Run `python scripts/quality.py`, documentation verification, delivery checks, telemetry/retrieval benchmarks, and the temporary rollback exercise.
3. Regenerate the SBOM from `uv.lock`; review vulnerability, license, secret, and static-security results under the triage policy.
4. For migrations, attach backup identifiers, dry-run reports, post-validation, approval for exact paths, and rollback steps.
5. Build an immutable image tag, smoke it as non-root with temporary volumes, verify liveness/readiness/auth/degraded behavior, and send SIGTERM.
6. Complete `RELEASE_READINESS.md`, link evidence, update version/changelog, create the signed/annotated tag, and publish only through an approved destination.
7. Upgrade using the container runbook, observe budgets/errors, and retain the prior image/index/backups for the declared rollback window.

A missing artifact is a release blocker, not an implicit waiver. Public deployment, TLS/provider selection, and hosted monitoring remain separate operator decisions.
