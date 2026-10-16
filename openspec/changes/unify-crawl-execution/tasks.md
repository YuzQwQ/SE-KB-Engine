## 1. Regression and boundaries

- [x] 1.1 Add offline regressions for credentials, terminal fallback, task identity, structure, storage and conditional fetch.
- [x] 1.2 Enforce origin credentials, bounded raw/decompressed streams, deadlines, explicit transports and verified DNS connections.

## 2. Content and snapshots

- [x] 2.1 Preserve ordered nonduplicate technical blocks and full extraction input; normalize URLs conservatively and close legacy DB resources.
- [x] 2.2 Publish unique atomic crawl snapshots and correct streamed-payload persistence.

## 3. Shared execution

- [x] 3.1 Correct state-machine classification/retries/cache and browser safety, waits and cleanup; add bounded site-aware execution.
- [x] 3.2 Compose the shared crawl service and migrate CLI/Web/MCP acquisition while preserving public contracts and internal authentication boundaries.
- [x] 3.3 Bind Web job identity and cancellation; bound runner admission, history and resource shutdown.

## 4. Acceptance and delivery

- [x] 4.1 Measure the production cleaner on at least 50 annotated local cases; fix quality/resource assertions and add adapter integration tests.
- [x] 4.2 Run offline quality gate, 100-page regression, bounded 30-minute soak and strict OpenSpec validation; record explicit browser/measurement limitations.
- [x] 4.3 Update crawl operations, current task and handoff with implementation/rollback evidence; preserve unrelated work and do not commit/archive.
