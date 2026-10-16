# Service boundary inventory

Baseline captured on 2026-09-15 before intentional boundary hardening. “Read” means a non-mutating
service operation; “admin” means it starts work, changes configuration/state, reloads data, or writes
artifacts.

## REST API (`api/`)

| Method/path | Role before change | Inputs | Success shape | Current failure/degraded behavior |
| --- | --- | --- | --- | --- |
| `POST /api/v1/search` | read bearer | JSON `query`, `intent`, `top_k`, `smart_search` | `{code,message,data}` | ad-hoc `{code,message}`; retriever absence is 503; exceptions leak `str(e)` |
| `GET /api/v1/health` | public | none | `{code,status,service,version}` | combines liveness/readiness in one 200 response |
| `POST /api/v1/admin/reload` | admin bearer | none | `{code,message,data.stats}` | exceptions leak `str(e)` |
| `GET /api/v1/admin/stats` | admin bearer | none | `{code,data}` | missing retriever is 503 |

Authentication accepted malformed/raw tokens, used ordinary membership comparison, and had no
correlation or audit event. The module runner enabled Flask debug mode.

## Browser Web API (`web/`)

| Method/path | Mutation/role | External/path inputs | Success shape before change |
| --- | --- | --- | --- |
| `GET /` | public page | none | HTML |
| `POST /api/start` | admin | `query`, `limit`, `types` | `{message}` |
| `POST /api/crawl-url` | admin/fetch | `url`, `extract`, `types` | `{message}` |
| `GET /api/status` | read | none | task-manager state object |
| `GET /api/types` | read | none | type array |
| `GET /api/url-index` | admin metadata | none | stats plus recent URLs |
| `POST /api/url-index/clear` | admin | none | `{message,total_urls}` |
| `POST /api/refine/start` | admin | `date`, `time`, `dry_run` | `{message}` |
| `GET /api/refine/status` | read | none | refine-manager state object |
| `POST /api/refine/preview` | admin | `date`, `time` | refiner preview object |
| `GET /api/artifacts/dates` | read | filesystem date components | string array |
| `GET /api/artifacts/times` | read | query `date` | time/count array |
| `POST /api/semantic-search` | read | `query`, `intent`, `top_k` | `{query,intent,total_found,results}` |
| `POST /api/system/reload-kb` | admin | none | `{message}` |

The Web API had no authentication or CSRF/origin enforcement, enabled unrestricted CORS, and used
several client-visible exception strings. Background start responses are intentionally preserved.

## MCP tools (`server.py`)

| Category | Tools | Boundary inputs / intended role |
| --- | --- | --- |
| Search/read | `fetch_raw_data`, `parse_search_results`, `search_and_parse_universal`, `get_available_search_engines`, `search_knowledge`, `get_dfd_generation_context`, `search_and_scrape_realtime`, `search_and_scrape` | keyword, engine, result limits, JSON rules; read role |
| Direct fetch | `scrape_webpage`, `crawl_webpage_direct` | user URL, headers/cookies, save flag; admin role when saving |
| Extraction/conversion | `extract_universal_knowledge`, `extract_knowledge_with_ai`, `convert_to_universal_format` | content, optional source URL, JSON; read role unless external model configured |
| Persistent mutation | `configure_search_engine`, `save_to_knowledge_base`, `save_universal_knowledge_base`, `manage_web_deduplication` (`clean`/`reset`) | config JSON, filenames/output paths/actions; admin role |
| Tor/admin diagnostics | `check_tor_ip`, `test_tor_connection`, `validate_tor_config`, `get_tor_bootstrap_status`, `auto_rotate_tor_identity`, `get_tor_circuit_info` | network/control-port operations; admin role |

MCP currently relies on the transport trust boundary and has no request credential context. This
change adds an explicit optional authorization field for administrative tools; deployments may keep
trusted-local mode explicit, but network-exposed MCP must configure service keys.

## URL-producing and URL-consuming paths

- Direct input: Web `/api/crawl-url`; MCP `scrape_webpage` and `crawl_webpage_direct`; manual scripts.
- Search result URLs: `utils/crawler_framework.py`, `web/services.py`, and both MCP search-and-scrape
  flows.
- HTTP fetch: `utils/webpage_crawler.py`, `server.py`, `utils/webpage_storage.py`, model/image
  adapters, Tor diagnostics, and search providers.
- Secondary resources: HTML image `src` values normalized by `utils/html_cleaner.py`, then fetched by
  `utils/webpage_storage.py` or vision helpers.
- Browser navigation: Playwright fallback in `utils/webpage_crawler.py`.

User/content URLs require the shared public-address policy. Administrator-configured model/search
provider endpoints are configuration trust boundaries and are documented separately; they still use
timeouts and must never be reflected with credentials.

## Public error and exposure baseline

The API used incompatible `{code,message}` and `{error}` envelopes. Some handlers returned status
500 for an unavailable optional capability, and several returned raw exception strings. Web status
and result rendering inserted server-controlled strings with `innerHTML`. There were no body-size,
rate, concurrency, or common field limits. These are the confirmed regression targets for this
change.
