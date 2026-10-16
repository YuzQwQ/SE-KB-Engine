# REST, Web, MCP, and script interfaces

## REST

The API listens on port 8000 when run directly. Read operations require `Authorization: Bearer <read-or-admin-key>`; mutations and diagnostics require an admin key. Examples use fake credentials:

```text
GET /api/v1/live
GET /api/v1/ready
POST /api/v1/search
Authorization: Bearer fake-read-key
Content-Type: application/json
{"query":"DFD 外部实体","top_k":5}

GET /api/v1/admin/diagnostics
Authorization: Bearer fake-admin-key
```

Every response has `X-Correlation-ID`; errors include the same safe identifier. `/live` is public and process-only. `/ready` returns 503 when required retrieval is unavailable. Admin diagnostics expose safe capability and low-cardinality metric summaries, never credentials or page/model bodies.

Search is read-only against the index but may initialize local Chroma state at process start. Admin reload mutates in-memory/index handles. Crawl and model routes can access the network, write artifacts, and incur provider cost; job IDs are returned for observation/cancellation.

## Web

The Web console is a separate Flask process on port 8000. Browser mutations require an admin bearer, an exact allowed Origin, and the CSRF header/cookie pair. It starts background crawl/refine jobs and therefore may access networks, models, and persistent data.

## MCP

`server.py` is a stdio MCP server; it has no HTTP port. Read tools validate input and use read authorization when a credential is configured. Configuration, cache clearing, crawl, extraction, or other mutations require admin authorization. Tool descriptions and responses distinguish operations that access networks, call paid models, or write corpus/artifact/index data. Pass fake credentials only in examples; real credentials belong in the MCP host's secret environment.

## Scripts

Offline/no-cost/read-only unless an explicit output is supplied: `quality.py`, `scan_artifacts.py`, `run_retrieval_benchmark.py`, `inventory_observability.py`, `benchmark_telemetry.py`, `check_docs.py`, and `check_delivery.py`.

Potentially mutating: `migrate_artifacts.py --execute`, `build_retrieval_index.py --mode full|incremental --switch`, crawl scripts, extraction/refinement scripts, and active-index reload. Migration and switching require review of exact source and target paths. Network/LLM/browser scripts can incur cost and are never part of default CI.
