## ADDED Requirements

### Requirement: Safe shared acquisition
Production Web, MCP and CLI acquisition SHALL use one bounded policy with at most three transient static attempts, one permitted rendered fallback, a shared deadline and explicit transport selection.

#### Scenario: Terminal policy failure
- **WHEN** a target, redirect, media type or response violates policy
- **THEN** no browser, third-party forwarding or alternate transport is attempted

#### Scenario: Cross origin redirect
- **WHEN** a credentialed page redirects to another origin
- **THEN** Authorization and origin-scoped cookies are not forwarded and the new target is independently validated

#### Scenario: Bounded body and time
- **WHEN** a chunked/compressed response or retries exhaust configured bytes or deadline
- **THEN** the operation closes resources and returns a typed failure without publishing partial content

### Requirement: Faithful technical documents
The pipeline SHALL preserve ordered headings, paragraphs, code whitespace, tables and useful links without nested duplicate blocks in parsed output and model input.

#### Scenario: Nested technical content
- **WHEN** an article contains pre/code, nested quotes, lists and tables
- **THEN** each semantic block occurs once and code/table values reach extraction input

### Requirement: Isolated cancellable jobs
Each worker SHALL bind a stable job identity, observe cancellation before subsequent external work and publication, and use bounded admission and history retention.

#### Scenario: Cancel and replace
- **WHEN** a running task is cancelled and another task is submitted
- **THEN** late events remain attached to the original task and the cancelled task cannot publish or start a new external stage

### Requirement: Traceable snapshots and cache
Snapshots SHALL have unique collection identities and atomic publication. URL identity SHALL preserve path case and semantic parameters. Conditional requests SHALL require a cached body and reuse it on 304.

#### Scenario: Same second collection
- **WHEN** two pages with the same title are collected in the same second
- **THEN** both raw and parsed results remain available at distinct locations

### Requirement: Controlled browser and site policies
Rendered acquisition SHALL isolate contexts, validate subrequests, reject interception failures and release owned resources. Automatic batches SHALL apply cached robots and per-host timing policies.

#### Scenario: Missing browser or unknown robots
- **WHEN** the selected optional browser is unavailable or automatic access policy cannot be determined
- **THEN** the result explicitly reports unavailable/unknown policy without an implicit external fallback

### Requirement: Offline production acceptance
Regression tests SHALL exercise production adapters and the production cleaner with annotated local pages, actual computed quality metrics and owned-resource checks.

#### Scenario: Quality measurement
- **WHEN** the local annotated corpus is measured
- **THEN** the report computes body precision/recall, metadata completeness and structural retention rather than constants or whole-page length ratios
