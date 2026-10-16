## Why

Long-running search and crawl work needs bounded concurrency, cancellation, retries, cleanup, and durable status. Current fallback chains and global Web task state can duplicate requests, lose failure context, race under concurrency, and leak browser/network resources.

## What Changes

- Define a bounded fetch state machine for static HTTP, rendered-browser, proxy, and direct fallbacks.
- Add connection pooling, phase-specific timeouts, retry/backoff, per-host limits, backpressure, conditional requests, and failure classification.
- Introduce explicit job IDs and queued/running/succeeded/failed/cancelled transitions with thread-safe progress and cancellation propagation.
- Guarantee cleanup for responses, files, browser contexts, workers, Tor processes, and realtime event subscribers.
- Add local mock-server, concurrency, cancellation, restart, and resource-leak tests.

Non-goals: bypassing access controls or CAPTCHAs, distributed crawling, a cloud queue, broad live crawling, or changing extracted knowledge semantics.

Prerequisites: `stabilize-runtime-and-quality`, `harden-service-boundaries`, and the service seams from `modularize-application-core`.

## Capabilities

### New Capabilities
- `resilient-crawling`: Crawls follow a bounded, observable, cancellable network and fallback policy.
- `managed-jobs`: Long-running operations have isolated identity, lifecycle, progress, cancellation, and recovery semantics.

### Modified Capabilities

None.

## Impact

Affects crawler utilities, Playwright and Tor integration, Web task services, MCP realtime tools, HTTP client configuration, state persistence, and tests. Live network validation remains opt-in and rate limited.
