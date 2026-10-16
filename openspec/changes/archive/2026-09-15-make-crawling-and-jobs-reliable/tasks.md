## 1. Characterize and model crawl behavior

- [x] 1.1 Build a local HTTP fixture server for success, redirects, retry responses, delay, compression, malformed encoding, large body, challenge, and disconnect cases.
- [x] 1.2 Record existing static, Playwright, proxy, Tor, and direct fallback decisions against the fixture server.
- [x] 1.3 Define typed fetch policy, attempt, transition, content classification, and final outcome models.
- [x] 1.4 Implement the finite fetch state machine and tests proving success avoids unnecessary retries/fallbacks.

## 2. Network resilience and resource bounds

- [x] 2.1 Introduce reusable HTTP client lifecycle with connection pooling and phase-specific timeouts.
- [x] 2.2 Implement typed retryability, exponential backoff with jitter, Retry-After, maximum attempts, and deterministic clock tests.
- [x] 2.3 Add global and per-host concurrency gates plus a bounded queue/backpressure policy.
- [x] 2.4 Stream and bound remote bodies, compression expansion, media processing, and total operation time.
- [x] 2.5 Add conditional request metadata and canonical/final URL deduplication without changing user data in place.
- [x] 2.6 Make Playwright contexts isolated, resource-filtered, timeout-bound, and always closed.
- [x] 2.7 Make Tor process/control lifecycle explicit and verify cleanup on startup failure, timeout, and shutdown.

## 3. Managed job lifecycle

- [x] 3.1 Define immutable job submission, job state, progress, event, result reference, and transition table models.
- [x] 3.2 Implement a thread-safe in-process `JobStore` and test invalid transitions, simultaneous reads, and terminal-state races.
- [x] 3.3 Replace global Web task/refine status with job IDs and isolated job state while providing a temporary compatibility view.
- [x] 3.4 Propagate cooperative cancellation through queues, HTTP, browser, model boundaries, extraction checkpoints, and publication.
- [x] 3.5 Add bounded per-job event history or cursor streaming and remove unbounded global log accumulation.
- [x] 3.6 Mark orphaned non-terminal jobs interrupted at startup or implement the explicitly selected resume policy.
- [x] 3.7 Add graceful shutdown that stops admission and cancels/waits for work within a configured deadline.

## 4. Failure, leak, and soak verification

- [x] 4.1 Test queued/running cancellation, timeout/cancel races, late worker completion, partial failure, and restart semantics.
- [x] 4.2 Verify HTTP responses, clients, browser contexts, file handles, threads, Tor processes, and subscriptions return to baseline after failures.
- [x] 4.3 Run an offline concurrent soak against the local fixture server and report throughput, p95 latency, memory, handles, queue depth, and error classes.
- [x] 4.4 Document crawl policy, retry/fallback rules, capacity settings, cancellation, challenge handling, and opt-in live validation.
