## Context

Multiple entry points directly create global clients and duplicate orchestration. The refactor must preserve behavior while introducing seams needed by later reliability and evaluation work.

## Goals / Non-Goals

**Goals:** explicit composition and lifecycle; typed settings and errors; small application services; thin adapters; compatibility during incremental extraction.

**Non-Goals:** framework rewrite, algorithm changes, or immediate relocation of every package into `src/`.

## Decisions

1. Add a plain-Python composition root rather than a DI framework. Constructor injection and protocols are sufficient and easier to debug.
2. Separate adapters (MCP/Flask/CLI), application orchestration, domain data, and infrastructure clients. Existing modules can implement protocols during migration.
3. Load immutable settings once per application instance with documented precedence; tests construct settings directly.
4. Define typed domain errors with public code, retryability, safe message, and wrapped cause. Boundary adapters own transport mapping.
5. Extract one vertical capability at a time behind characterization tests; retain imports/tool names through deprecation shims.

## Risks / Trade-offs

- [Large diff or circular imports] → extract leaf services first and enforce dependency direction.
- [Compatibility shim becomes permanent] → give each shim an owner and removal criterion.
- [Global state behavior changes] → characterize startup/lifecycle and inject clocks/stores in tests.

## Migration Plan

Introduce domain errors/settings; add composition root; extract client factories; then search, Tor, crawling, visual, extraction, retrieval, and events one by one. Compare contracts after every extraction. Rollback uses existing facade implementations.

## Open Questions

- Whether the long-term package root should be `src/se_kb_engine` is deferred until imports are stable.
