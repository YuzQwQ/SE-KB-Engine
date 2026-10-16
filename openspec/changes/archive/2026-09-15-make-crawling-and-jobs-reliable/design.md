## Context

Crawling crosses synchronous and asynchronous code, HTTP clients, browsers, proxies, Tor, files, and UI status. Reliability requires one policy and one job lifecycle rather than nested fallback exceptions and global mutable status.

## Goals / Non-Goals

**Goals:** bounded fetch state machine; reusable clients; correct retries; backpressure; cancellation; isolated job state; cleanup and recovery tests.

**Non-Goals:** distributed crawling, bypass techniques, or an external queue as a first step.

## Decisions

1. Represent attempts and transitions explicitly: validate → static fetch → classify → optional rendered fallback, with proxy/direct policy decided before execution.
2. Retry only typed transient errors using exponential backoff with jitter and Retry-After; record every attempt.
3. Use bounded global and per-host semaphores/queues. Never create unbounded threads or browser contexts.
4. Introduce a `JobStore` abstraction with an in-process transactional implementation first; persist only when restart requirements prove necessary.
5. Cancellation is cooperative and propagated via a token/event to all stages; every resource uses context-managed cleanup.

## Risks / Trade-offs

- [More conservative crawling reduces success on hostile sites] → report challenge/login states rather than unsafe bypass.
- [Cancellation cannot interrupt a blocking dependency] → enforce short phase timeouts and isolate the dependency.
- [In-process jobs are lost on crash] → mark interrupted jobs on restart; evaluate persistence separately.

## Migration Plan

Characterize existing crawler; add typed results/policy; introduce pooled client and state machine; then route Web/MCP operations through managed jobs. Keep legacy synchronous facade until parity tests pass.

## Open Questions

- Is restart-resumable crawling required, or is explicit interrupted status sufficient?
