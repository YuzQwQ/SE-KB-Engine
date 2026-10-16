# `server.py` modularization baseline

Captured 2026-09-15. This is the compatibility ledger for incremental extraction; it complements
`SERVICE_BOUNDARY_INVENTORY.md`, which records transport-level routes and security behavior.

## Module globals and import-time behavior

| Area | Globals/collaborators | Import-time behavior before extraction |
| --- | --- | --- |
| MCP | `mcp` | Creates `FastMCP("WebScrapingServer")` and registers 23 decorated tools |
| configuration | model/search/Tor constants, prompt dictionary | Loads `.env` unless explicitly disabled; reads prompt and parser configuration |
| extraction | `format_processor`, `universal_processor` | Constructs processors and reads optional format configuration |
| retrieval | `knowledge_retriever`, `query_planner` | Attempts Chroma/OpenAI-compatible vector initialization and reports degraded globals on failure |
| search | `crawler`, `default_search_engine` | Constructs `CrawlerFramework` and reads parser JSON files |
| crawl/storage | deduplication/storage singleton accessors | Lazily opens SQLite/filesystem state when operations call them |
| Tor | configuration constants, optional `tor_manager` | Previously constructed process manager at import; startup/control belongs behind lifecycle |
| events | `websocket_connections` | Mutable process-global subscriber collection |
| model | lazy `openai_client` | Client now initializes on first model operation rather than import |

Import must not start an MCP server, browser, Tor process, network request, or paid model call. Current
compatibility tests run import and `list_tools()` with outbound networking blocked.

## Side-effect ledger

- Filesystem reads: `.env`, prompt/config JSON, parser definitions, vector configuration.
- Filesystem writes: crawl raw/parsed data, artifacts, knowledge-base exports, SQLite dedup state, Tor
  state/logs. These occur only inside invoked operations and must use injected roots.
- Network: search provider, direct HTTP fetch, redirect/image fetch, OpenAI-compatible model calls,
  Playwright page/subresource navigation, Tor diagnostics/control.
- Processes: Playwright browser and optional Tor executable. Both require explicit application
  startup/use and explicit close.
- Mutable state: retriever/planner readiness, search engine registry, dedup cache, task/event
  subscribers, and lazily created HTTP/model clients.

## MCP compatibility surface

The exact 23 tool names and argument-property sets are executable in
`tests/contracts/mcp_tool_contracts.json`. Categories are search/parser (4), configuration (1), Tor
(6), retrieval/context (2), crawl (2), extraction/conversion/storage (5), combined crawl flows (2),
and dedup administration (1). Administrative tools retain explicit authorization and correlation
arguments introduced by service-boundary hardening.

## Duplicated operation flows

- Semantic retrieval exists in MCP `search_knowledge`, REST `/api/v1/search`, and Web
  `/api/semantic-search`.
- Crawl orchestration exists in MCP scrape/search-and-scrape tools, `web/services.py`, and crawler
  scripts.
- Retriever creation/reload exists in `server.py`, `api/app.py`, API admin reload, Web service setup,
  and Web reload.
- Search-provider parsing/configuration is split between MCP functions and `CrawlerFramework`.
- Knowledge extraction and storage are composed separately by MCP, Web services, and scripts.
- Task feedback is held by MCP websocket globals and Web task/refine managers.

Compatibility facades remain until parity tests show every runtime adapter calls the shared service.
