# SE-KB-Engine OpenSpec optimization roadmap

The optimization backlog is split into seven independently reviewable changes. Apply and archive them in this dependency order unless a task explicitly has no dependency on unfinished behavior.

1. `stabilize-runtime-and-quality` — encoding, runtime/dependencies, import safety, tests, and quality gates.
2. `harden-service-boundaries` — authentication, browser mutations, SSRF, bounded inputs, and public contracts.
3. `modularize-application-core` — settings/errors, composition, lifecycle, and incremental `server.py` extraction.
4. `make-crawling-and-jobs-reliable` — bounded fetch state machine, concurrency, jobs, cancellation, and cleanup.
5. `version-artifacts-and-extraction` — manifests, atomic writes, integrity/migration, grounded extraction, and idempotent refinement.
6. `evaluate-and-optimize-retrieval` — offline relevance benchmark, index compatibility, experiments, and promotion gates.
7. `productionize-observability-and-delivery` — telemetry, CI, containers, release/rollback, runbooks, and accurate docs.

The original detailed source list remains in `docs/PROJECT_OPTIMIZATION_BACKLOG.md`. OpenSpec artifacts are the implementation source of truth; the backlog is supporting discovery material.

## Execution guardrails

- Start a change only when its prerequisite contracts are implemented or explicitly stubbed and protected by tests.
- Apply tasks in small batches and run the nearest offline verification after each batch.
- Never modify real corpus, vector index, generated copyright output, credentials, logs, or unrelated working-tree changes unless a task and the user explicitly authorize it.
- Network, browser, Tor, Docker, and paid model execution remain opt-in.
- Archive a change only after its specs, task checkboxes, tests, migration/rollback notes, and documentation are complete.
