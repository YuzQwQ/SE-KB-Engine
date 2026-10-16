## Context

The approved review documents multiple production acquisition paths and disconnected crawl/job components. Preserve all pre-existing working-tree changes and data. Existing adapter contracts and offline-first tests remain authoritative.

## Goals / Non-Goals

Goals: one production fetch policy, origin-scoped credentials, bounded execution, faithful technical blocks, cancellable jobs and traceable snapshots. Non-goals: distributed crawling, replacing HTTPX/BeautifulSoup, live scraping, paid calls, automatic data migration, automatic index publication or unconditional parser replacement.

## Decisions

- Keep domain request/result protocols; extend fetch results with final/requested URL, payload metadata and execution context. Inject the crawl service in composition; legacy WebpageCrawler becomes a compatibility facade.
- Use a single 60-second crawl deadline, three transient static attempts and at most one isolated rendered fallback. Policy/challenge/permanent failures terminate. Explicit proxy/Tor failures never silently become direct requests. Conditional headers require a bounded cached body.
- Prepare each HTTP request explicitly so cross-origin redirects strip sensitive headers and cookies. Production direct transports bind verified DNS addresses to connections while preserving Host/TLS origin. Stream raw and incrementally decoded bytes under both bounds. Disable ambient proxies for controlled acquisition.
- Browser execution is serialized in a dedicated owner thread; contexts are isolated. Context-wide routes, disabled service workers and rejection on interception failure are mandatory. Browser capability is optional; absence produces a typed outcome. Browser OS-level egress containment and true browser tests remain explicit deployment validation, never an invented guarantee.
- Preserve ordered blocks (headings 1-6, paragraphs, quotes, lists, code, tables, links); render all downstream representations from these blocks. Publish unique raw/parsed snapshots atomically without rewriting old data.
- Web tasks bind job identity using execution context, with bounded admission and cancellation checkpoints before external work and publication. Retain legacy JSON and job headers. Share a 4-global/1-host capacity with 16 waiting admissions; use per-host timing and cached robots for automatic batches. Unknown robots policy fails closed.
- MCP adapters authenticate once and call internal services. Blocking work runs in bounded executors. Separate target acquisition credentials from model/image-client credentials.
- Bounded TTL histories/cache and explicit close methods prevent lifetime growth. Benchmark the production cleaner and entrypoints against at least 50 annotated local cases. Measure real precision/recall and structure retention; do not claim RSS from tracemalloc.

## Risks / Trade-offs

- Stricter policy can turn historical fallback success into explicit failure; this is intentional and documented.
- Parser output changes content identities; version new snapshots and never migrate existing files implicitly.
- Windows/optional Playwright availability limits native validation; offline fakes verify contracts and actual browser checks stay separate.
- Python cannot forcibly cancel arbitrary model SDK work; cancellation blocks subsequent stages and publishing, while in-flight work obeys its configured timeout.

## Migration Plan

First add regression fixtures, then fix network/content/job boundaries. Wire the shared service via compatibility facades and migrate CLI, Web and MCP; preserve public contracts with focused integration tests. Run offline gate and strict validation. Roll back per adapter while retaining security fixes; preserve all old snapshots. No commit or archive without user instruction.
