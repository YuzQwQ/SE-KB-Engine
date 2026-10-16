## Why

`server.py` combines configuration, Tor lifecycle, search, crawling, visual processing, extraction, storage, retrieval, and realtime feedback in one large module with global state and broad exception handling. This prevents isolated testing and causes behavior to diverge between MCP, Web, API, and scripts.

## What Changes

- Introduce a typed application composition root and explicit lifecycle for settings, clients, stores, and services.
- Unify configuration precedence, path resolution, external client construction, error taxonomy, retryability, and response mapping.
- Incrementally extract search, Tor, crawl orchestration, visual processing, extraction, retrieval, and event publishing from `server.py`.
- Keep existing MCP tool names and contracts through thin compatibility adapters while call sites migrate.
- Remove duplicated implementations only after characterization and contract tests prove equivalence.

Non-goals: rewriting the project in another framework, adopting a dependency-injection framework, changing data formats, or changing crawler/RAG algorithms.

Prerequisites: `stabilize-runtime-and-quality`; boundary contracts from `harden-service-boundaries` must remain protected during extraction.

## Capabilities

### New Capabilities
- `application-composition`: Runtime dependencies and lifecycle are explicitly assembled and can be replaced in tests.
- `unified-configuration-errors`: All surfaces share typed configuration, error categories, retry semantics, and safe response mapping.

### Modified Capabilities

None.

## Impact

Affects `server.py`, `registry.py`, `llm_client.py`, `utils/env_loader.py`, Web/API service setup, and newly introduced application modules. The work is an incremental internal refactor with compatibility layers and no intended public contract break.
