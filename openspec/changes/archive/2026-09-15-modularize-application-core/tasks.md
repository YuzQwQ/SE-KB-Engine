## 1. Characterization and dependency map

- [x] 1.1 Catalog `server.py` globals, import-time effects, MCP tools, collaborators, filesystem/network/process actions, and duplicated Web/API/script flows.
- [x] 1.2 Capture golden contracts for each MCP tool and shared operation, including failure and degraded cases.
- [x] 1.3 Generate an import/dependency map and define allowed adapter → application → domain → infrastructure directions.

## 2. Shared domain foundations

- [x] 2.1 Introduce immutable typed settings with documented precedence and tests for invalid/sensitive values.
- [x] 2.2 Centralize project/config/data/cache/output root resolution and test startup from a non-project working directory.
- [x] 2.3 Define typed application errors with public code, safe message, retryability, metadata, and wrapped cause.
- [x] 2.4 Replace message-substring retry decisions in one vertical path with typed errors and regression tests.
- [x] 2.5 Define domain DTOs/protocols only for boundaries needed by search, fetch, extraction, storage, retrieval, jobs, and events.

## 3. Composition and client lifecycle

- [x] 3.1 Add an application composition root that accepts settings and constructs replaceable clients, stores, services, clock, and logging context.
- [x] 3.2 Move OpenAI-compatible, HTTP, vector-store, browser, and Tor client creation behind factories with explicit lifecycle.
- [x] 3.3 Make application startup clean up already-created resources after partial failure and expose capability readiness.
- [x] 3.4 Adapt MCP, REST, Web, and CLI entry points to receive an application instance while retaining compatibility entry points.

## 4. Incremental vertical extraction

- [x] 4.1 Extract prompt/config loading and search-engine registry/parsing behind tested services.
- [x] 4.2 Extract Tor process/control operations and remove their module-import startup side effects.
- [x] 4.3 Extract crawl orchestration and direct/rendered fallback coordination while retaining crawler implementation behavior.
- [x] 4.4 Extract visual analysis, knowledge extraction, validation, and artifact-saving orchestration.
- [x] 4.5 Extract retrieval/DFD-context and realtime event publishing services.
- [x] 4.6 Convert MCP decorators and Flask handlers into thin validation/auth/call/map adapters.

## 5. Convergence and verification

- [x] 5.1 Route duplicate Web/API/script implementations through shared application services and delete duplication only after parity tests pass.
- [x] 5.2 Narrow broad exceptions at extracted boundaries and replace silent `pass` with explicit ignore rationale or diagnostics.
- [x] 5.3 Add architecture tests or lint rules that prevent infrastructure/transport imports from leaking into domain modules.
- [x] 5.4 Run all characterization, boundary, import, type, and offline integration tests after each vertical extraction.
- [x] 5.5 Document the module map, lifecycle, compatibility shims, removal criteria, and deferred `src/` migration decision.
