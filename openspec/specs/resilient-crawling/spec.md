# Resilient crawling

## Purpose

Define bounded, observable, cancellable crawling with classified outcomes and deterministic fallback behavior.

## Requirements

### Requirement: Bounded fetch state machine
Every crawl SHALL execute through an explicit state machine with a finite set of attempts and a recorded reason for each fallback.

#### Scenario: Static page succeeds
- **WHEN** validated static HTTP fetching returns acceptable content
- **THEN** the crawl completes without launching a browser or repeating the request

#### Scenario: Unsupported fallback
- **WHEN** an error is permanent or policy-blocked
- **THEN** the crawl fails without trying unrelated proxy, direct, or browser paths

### Requirement: Controlled concurrency and retries
Crawling SHALL enforce global and per-host concurrency, bounded queues, phase timeouts, and typed transient retry policy.

#### Scenario: Queue capacity reached
- **WHEN** producers exceed configured capacity
- **THEN** they receive backpressure or a bounded rejection rather than unbounded memory growth

### Requirement: Resource cleanup
HTTP responses, clients, browser contexts, files, Tor processes, and subscriptions SHALL close on success, failure, timeout, and cancellation.

#### Scenario: Cancellation during browser fetch
- **WHEN** a job is cancelled during rendered navigation
- **THEN** navigation stops, the context closes, and the job reaches cancelled state

### Requirement: Classified crawl outcome
Each crawl SHALL record final URL, timing, attempts, status/media metadata, and a typed success, challenge, no-content, policy, transient, or permanent failure.

#### Scenario: Login wall
- **WHEN** fetched content is classified as a login or challenge page
- **THEN** it is not published as successfully extracted article content
