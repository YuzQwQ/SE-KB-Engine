## ADDED Requirements

### Requirement: Correlated structured events
Runtime events SHALL use centralized configuration and carry safe correlation, job, document, stage, attempt, outcome, and duration fields where applicable.

#### Scenario: Pipeline failure trace
- **WHEN** an extraction job fails after crawling
- **THEN** an operator can correlate entry, crawl attempts, extraction failure, and terminal job state without searching page content

### Requirement: Sensitive and bounded telemetry
Telemetry SHALL redact credentials and private headers, avoid full content/model bodies by default, bound field sizes, and avoid high-cardinality metric labels.

#### Scenario: Upstream error contains token
- **WHEN** an exception message includes a credential-like value
- **THEN** public and operator telemetry replace it with a redaction marker

### Requirement: Stage health and budgets
The system SHALL expose bounded metrics for request/job volume, stage success/failure/latency, retries, queues, cache, LLM tokens/cost, index/retrieval, and resource pressure.

#### Scenario: Budget threshold reached
- **WHEN** a configured task token, concurrency, response, or disk budget is reached
- **THEN** work stops or degrades according to policy and emits a correlated budget event

### Requirement: Distinct liveness and readiness
Liveness SHALL report process responsiveness, while readiness SHALL report required capability availability with safe reasons.

#### Scenario: Retriever unavailable
- **WHEN** the process is responsive but the required index cannot load
- **THEN** liveness succeeds and readiness reports degraded or unavailable
