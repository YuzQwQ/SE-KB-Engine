## 1. Central logging and correlation

- [x] 1.1 Inventory every `basicConfig`, print, logger, large/sensitive payload, health signal, and existing metric source.
- [x] 1.2 Configure logging once at composition and remove module-level competing configuration without changing log destinations unexpectedly.
- [x] 1.3 Define structured event fields and propagate request, job, document, stage, attempt, and outcome context across all runtime surfaces.
- [x] 1.4 Implement credential/header/content redaction and bounded field serialization with adversarial tests.
- [x] 1.5 Add correlated error reporting that links safe public errors to sanitized operator diagnostics.

## 2. Health, metrics, and budgets

- [x] 2.1 Separate liveness, readiness, and admin diagnostics with authorization and dependency-specific safe reasons.
- [x] 2.2 Instrument request/job volume, stage duration/outcomes, crawl attempts, retries, queue depth, cache, and resource cleanup.
- [x] 2.3 Instrument extraction/schema outcomes, LLM token/latency/cache/estimated cost, and per-task budget exhaustion.
- [x] 2.4 Instrument index size/build and retrieval quality/latency/no-answer behavior using low-cardinality labels.
- [x] 2.5 Add configurable concurrency, response, token, time, memory/disk warning, and queue budgets with correlated policy events.
- [x] 2.6 Benchmark telemetry overhead and enforce payload/cardinality bounds.

## 3. Cross-platform CI and supply chain

- [x] 3.1 Add required Windows/Linux jobs for encoding/compile, Ruff, mypy, and deterministic offline pytest on the supported Python matrix.
- [x] 3.2 Cache dependencies using lock/platform keys and verify authoritative dependency drift.
- [x] 3.3 Upload sanitized coverage, benchmark summary, and failure artifacts with explicit retention.
- [x] 3.4 Add manually triggered or scheduled browser/network/LLM/Tor/container suites with budgets, timeouts, and least-privilege secrets.
- [x] 3.5 Add secret, dependency vulnerability, license, static security, and SBOM checks with a documented triage policy.
- [x] 3.6 Add fast pre-commit hooks and ratchet Ruff/mypy exclusions by scoped category rather than mass formatting.

## 4. Container and gateway hardening

- [x] 4.1 Add `.dockerignore` and a multi-stage image using the supported Python and authoritative locked production dependencies.
- [x] 4.2 Minimize runtime content/packages, pin/update the base image deliberately, and run as non-root with a read-only root where feasible.
- [x] 4.3 Define/test writable data, cache, index, and log mounts and inject secrets without mounting a broad `.env` file.
- [x] 4.4 Tune Gunicorn worker/lifecycle/graceful-timeout settings from concurrency and memory measurements.
- [x] 4.5 Implement a healthcheck using guaranteed runtime tools and test startup, readiness, auth, degraded behavior, and shutdown.
- [x] 4.6 Harden Compose/Nginx resource/log limits, body/time limits, headers, TLS failure behavior, and trusted proxy/IP handling.

## 5. Release, runbooks, and accurate docs

- [x] 5.1 Define version source, changelog, tag, migration, compatibility, smoke, upgrade, rollback, and evidence checklist.
- [x] 5.2 Exercise container upgrade and rollback with temporary artifact/index copies and record the procedure.
  - Local temporary-copy and Docker Desktop exercises pass. `scripts/exercise_container_release.py` verified isolated old/new image tags, temporary named volumes, startup/auth, UID 10001, a read-only root, upgrade, rollback, byte-identical artifact/index digests, and scoped cleanup. Evidence: `docs/baseline/container-release-exercise-2026-09-16.json`.
- [x] 5.3 Correct README architecture, directory names, entry points, ports, dependency setup, and offline/full quick starts.
- [x] 5.4 Document all settings with precedence, sensitivity, defaults, side effects, data locations, backups, and retention.
- [x] 5.5 Document REST and MCP contracts with fake-key examples and explicit network/cost/mutation annotations.
- [x] 5.6 Add runbooks for missing keys, proxy/Tor, browser, index, model, rate limit, disk, corrupt artifacts, stuck jobs, and rollback.
- [x] 5.7 Add automated checks for documentation links and executable offline setup/smoke commands.
- [x] 5.8 Produce a release-readiness report linking CI, security, SBOM, smoke, performance, migration, documentation, and remaining risks.
