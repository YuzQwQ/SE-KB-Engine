# Configuration reference

Precedence is: explicit application override, process environment, `config/application.toml` (or explicitly selected JSON/TOML), then documented default. Legacy entry points also load a local `.env`; production containers do not mount one and receive secrets through the process environment.

| Setting | Default | Sensitive | Effect |
|---|---:|:---:|---|
| `SE_KB_PROJECT_ROOT` | repository root | no | Root used to resolve other paths. |
| `CONFIG_ROOT` | `<root>/config` | no | Prompt and application configuration. |
| `DATA_ROOT` | `<root>/data` | possibly | Raw/parsed and application state; back up per data-owner policy. |
| `CACHE_ROOT` | `<root>/cache` | possibly | Rebuildable cache; deletion is not source-data deletion. |
| `OUTPUT_ROOT` | `<root>/output` | possibly | Generated results; retention follows artifact policy. |
| `OPENAI_API_KEY`, `KB_API_KEY`, `FILTER_API_KEY`, `EMBEDDING_API_KEY` | unset | yes | Enables paid/network model stages. Never log or commit. |
| `BASE_URL`, `KB_BASE_URL`, `FILTER_BASE_URL`, `EMBEDDING_BASE_URL` | provider-specific | no | Remote provider endpoints; network side effect. |
| `MODEL`, `KB_MODEL_ID`, `FILTER_MODEL_ID`, `EMBEDDING_MODEL_ID` | provider defaults | no | Model identity and compatibility/cost input. |
| `KB_READ_KEYS` | unset | yes | Comma-separated REST/MCP read credentials. |
| `KB_ADMIN_KEYS` | unset | yes | Comma-separated mutation/admin credentials. |
| `CORS_ORIGINS` | localhost 8000/8001 | no | Exact allowed browser origins; wildcard is unsupported. |
| `API_DEBUG` | `false` | no | Enables Flask debug only for local development. |
| `DEFAULT_SEARCH_ENGINE` | `google` | no | Search adapter selection; invokes network when used. |
| `HTTP_TIMEOUT_SECONDS` | `20` | no | Overall application HTTP timeout. |
| `HTTP_MAX_RETRIES` | `3` | no | Retry attempts, bounded 0–10. |
| `USE_TOR` | `false` | no | Enables Tor path; requires local executable/configuration. |
| `OBSIDIAN_VAULT_ROOT` | unset | possibly | Explicit local Vault directory. Unset keeps the integration disabled. |
| `OBSIDIAN_VAULT_NAME` | directory name | no | Vault name or ID used in encoded `obsidian://open` links. |
| `OBSIDIAN_MANAGED_DIRECTORY` | `SE-KB` | no | Relative Vault namespace owned by the exporter. Traversal and absolute paths are rejected. |
| `OBSIDIAN_ENTITY_KINDS` | `concept,rule,pattern,example` | no | Curated entity types eligible for standalone notes. Raw chunks stay inside source notes. |
| `OBSIDIAN_SEMANTIC_EDGES` | `true` | no | Includes labeled semantic suggestions when a provider is available. |
| `OBSIDIAN_SEMANTIC_MIN_SCORE` | `0.75` | no | Similarity threshold, bounded 0–1. |
| `OBSIDIAN_SEMANTIC_MAX_NEIGHBORS` | `5` | no | Per-node semantic edge ceiling, bounded 0–100. |
| `OBSIDIAN_GRAPH_NODE_LIMIT` | `500` | no | API/UI/Canvas graph ceiling, bounded 10–5000. |
| `OBSIDIAN_CANVAS_ENABLED` | `false` | no | Emits a deterministic JSON Canvas file through the same preview/conflict policy. |
| `TOR_EXECUTABLE_PATH`, `TOR_PASSWORD` | unset | password yes | Tor process path/control credential. |
| `MAX_REQUEST_BYTES` | `1048576` | no | Reject larger request bodies. |
| `MAX_QUERY_CHARS` | `4000` | no | Reject longer queries. |
| `MAX_TOP_K` | `100` | no | Public retrieval ceiling; optimized planner also clamps to 20. |
| `MAX_TASK_LIMIT` | `50` | no | Maximum submitted task item count. |
| `REQUESTS_PER_MINUTE` | `120` | no | Per-client/endpoint in-process limit. |
| `MAX_REQUEST_CONCURRENCY` | `16` | no | Concurrent request budget. |
| `MAX_RESPONSE_BYTES` | `4194304` | no | Per-task response budget. |
| `MAX_TOKENS_PER_TASK` | `100000` | no | Stops a task that exhausts its model-token budget. |
| `MAX_TASK_SECONDS` | `600` | no | Per-task elapsed-time budget. |
| `MAX_QUEUE_DEPTH` | `100` | no | Rejects/degrades work above the queue budget. |
| `MEMORY_WARNING_BYTES` | `1073741824` | no | Emits/stops according to policy at memory pressure. |
| `DISK_WARNING_FREE_BYTES` | `2147483648` | no | Minimum free-space warning/stop boundary. |
| `FETCH_MAX_REDIRECTS` | `5` | no | Redirect safety limit. |
| `FETCH_MAX_COMPRESSED_BYTES` | `8388608` | no | Compressed response ceiling. |
| `FETCH_MAX_DECOMPRESSED_BYTES` | `16777216` | no | Decompressed response ceiling. |
| `FETCH_MAX_IMAGE_PIXELS` | `40000000` | no | Image decode bomb guard. |
| `FETCH_TOTAL_SECONDS` | `60` | no | Total fetch deadline. |
| `ALLOW_PRIVATE_NETWORK_FETCH` | `false` | security-sensitive | Allows private targets only in explicitly trusted deployments. |
| `GUNICORN_WORKERS` | `2` | no | Container process count; raise only after memory/concurrency measurement. |
| `GUNICORN_THREADS` | `4` | no | Threads per worker. |
| `GUNICORN_TIMEOUT` | `60` | no | Hard worker request timeout. |
| `GUNICORN_GRACEFUL_TIMEOUT` | `30` | no | Shutdown drain window. |

`se_kb/`, `data/`, `cache/`, `output/`, and `logs/` can contain private or derived data. Backups, retention, legal holds, and deletion are owned by the data owner; see [artifact lifecycle](ARTIFACT_LIFECYCLE.md). Container mounts map these concerns to separate named volumes.

An Obsidian Vault can also contain private source URLs, extracted knowledge, aliases, and inferred semantic relationships. Review [Obsidian integration](OBSIDIAN_INTEGRATION.md) before enabling the projection or sharing a Vault.
