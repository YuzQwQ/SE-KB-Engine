## ADDED Requirements

### Requirement: Explicit Vault configuration and availability
The system SHALL keep Obsidian integration disabled until an operator explicitly configures a Vault root, SHALL validate the configured location before use, and SHALL expose availability without affecting acquisition or retrieval when the Vault is unavailable.

#### Scenario: Integration is not configured
- **WHEN** the application starts without a Vault root
- **THEN** normal acquisition and retrieval remain available and Vault status reports `not_configured`

#### Scenario: Configured Vault is unavailable
- **WHEN** status is requested for a missing or inaccessible configured Vault root
- **THEN** the system reports a non-sensitive diagnostic and performs no writes

### Requirement: Safe managed namespace
The system MUST restrict generated writes to a configured managed directory beneath the resolved Vault root and MUST reject traversal, absolute child paths, control characters, symlink or reparse-point escapes, and destinations outside that boundary.

#### Scenario: Valid managed destination
- **WHEN** a planned note resolves to a regular destination beneath the managed root
- **THEN** the note is eligible for preview and publication

#### Scenario: Destination escapes through a link
- **WHEN** a destination parent resolves outside the managed root through a symlink or reparse point
- **THEN** the export fails safely before writing the file and reports the offending logical path

### Requirement: Deterministic note projection
The system SHALL deterministically render selected source documents and curated knowledge entities as UTF-8 Markdown notes with valid YAML frontmatter, stable SE-KB identity, ownership marker, source attribution, content hash, note kind, and readable content.

#### Scenario: Repeated render of unchanged input
- **WHEN** the same valid artifacts and export configuration are rendered twice
- **THEN** note paths and content are identical except for fields explicitly defined as run metadata outside the content fingerprint

#### Scenario: Untrusted metadata contains syntax characters
- **WHEN** a title, tag, URL, or metadata value contains YAML delimiters, wiki-link delimiters, HTML, newlines, or Unicode characters
- **THEN** the exporter escapes or quotes the value so it remains data and cannot inject frontmatter fields or executable HTML

### Requirement: Stable identity and collision-safe paths
The system SHALL derive note identity and links from stable SE-KB identifiers and SHALL resolve title changes, reserved names, Unicode normalization, case-insensitive collisions, and path-length limits without merging distinct knowledge objects.

#### Scenario: Two notes share a title
- **WHEN** distinct SE-KB identities produce the same sanitized title
- **THEN** they receive distinct deterministic paths and links resolve to the intended notes

#### Scenario: Display title changes
- **WHEN** an existing knowledge object retains its identity but changes title
- **THEN** preview reports a rename or update, inbound generated links use the new mapped path, and the previous title is retained as an alias when valid

### Requirement: Meaningful note granularity
The system SHALL project source documents and configured curated entity kinds as notes and SHALL keep raw retrieval chunks within their parent note as headings or block anchors rather than standalone graph nodes by default.

#### Scenario: Document contains multiple chunks
- **WHEN** a selected document has several indexed chunks
- **THEN** the export creates one source note with addressable sections or blocks instead of one note per chunk

### Requirement: Relationship provenance
The system SHALL distinguish explicit relationships from semantic suggestions in both Markdown and relationship API output, and semantic edges MUST include score and method metadata.

#### Scenario: Explicit cross-reference is exported
- **WHEN** an artifact references another exported stable identity
- **THEN** the note contains a durable wiki link and the graph edge is labeled explicit with its relationship type

#### Scenario: Vector similarity suggests a relation
- **WHEN** two notes exceed the configured similarity threshold without an explicit relationship
- **THEN** the relation appears only as a labeled semantic suggestion with its score and method and is not represented as an asserted fact

### Requirement: Previewable incremental export
The system SHALL compute a complete export plan before publication and classify notes as create, update, rename, unchanged, conflict, skipped, or stale; dry-run MUST return the plan without changing Vault contents or exporter state.

#### Scenario: Dry-run preview
- **WHEN** an authenticated operator requests an export preview
- **THEN** the response reports categorized counts and bounded item details while all Vault file hashes and state remain unchanged

#### Scenario: Unchanged corpus
- **WHEN** the source fingerprint, export configuration, and exporter-owned file hashes match the last successful export
- **THEN** the plan classifies those notes as unchanged and does not rewrite them

### Requirement: Conflict-safe ownership
The system MUST NOT overwrite a managed note whose current content differs from the exporter-owned hash recorded at its last successful publication, and MUST NOT modify or delete unowned Vault files.

#### Scenario: User modified a generated note
- **WHEN** an exporter-owned note differs from its recorded published hash
- **THEN** the plan marks a conflict, preserves the file byte-for-byte, and continues processing independent notes

#### Scenario: Unknown file exists in managed directory
- **WHEN** an unrecorded file occupies a planned path
- **THEN** the exporter treats it as a conflict and does not overwrite or rename it

### Requirement: Atomic cancellable publication
The system SHALL publish planned changes using temporary files and atomic replacement where supported, SHALL commit exporter state last, SHALL prevent concurrent writers for the same managed root, and SHALL honor managed-job cancellation checkpoints.

#### Scenario: Successful publication
- **WHEN** all planned writes and verification complete
- **THEN** targets match the plan, exporter state references their published hashes, and the job completes successfully

#### Scenario: Failure before state commit
- **WHEN** publication fails or is cancelled before state is committed
- **THEN** no new state claims partial files as a successful projection and the next run can identify and clean temporary files safely

#### Scenario: Concurrent export attempt
- **WHEN** a second publication targets a managed root with an active writer
- **THEN** the second request is rejected or queued with an explicit non-success status and writes are not interleaved

### Requirement: Non-destructive stale-note handling
The system SHALL report notes no longer present in the selected source set as stale and SHALL retain them by default; any future destructive cleanup MUST require a separate explicit previewed operation.

#### Scenario: Source artifact is no longer selected
- **WHEN** a previously exported note is absent from the new source selection
- **THEN** preview and publication report it as stale without deleting or moving it

### Requirement: Authenticated additive API and managed jobs
The system SHALL expose Vault status, preview, export submission, export job status, relationship data, and note-location operations through additive REST contracts protected by the existing service authentication policy, with publication using the managed-job lifecycle.

#### Scenario: Unauthenticated export request
- **WHEN** a client without valid service authentication requests preview, export, relationships, or note location
- **THEN** the system rejects the request using the existing authentication error contract and performs no Vault access beyond what that policy permits

#### Scenario: Export job is submitted
- **WHEN** an authenticated operator submits a valid publication request
- **THEN** the response identifies a managed job whose progress, cancellation, terminal result, and errors follow existing job contracts

### Requirement: Safe Obsidian deep links
The system SHALL construct URL-encoded `obsidian://open` links from configured Vault identity and Vault-relative logical note paths, SHALL provide the path as a fallback, and MUST NOT start a desktop process on the server.

#### Scenario: Open-note link requested
- **WHEN** an authenticated client requests the location of an exported note
- **THEN** the response contains an encoded Obsidian URI and Vault-relative path without exposing unrelated host paths

#### Scenario: Obsidian is not installed
- **WHEN** a client cannot handle the returned URI
- **THEN** the server remains healthy and the user can still copy the returned Vault-relative path

### Requirement: Accessible bounded visualization
The Web console SHALL display Vault status, export controls, plan/results, and relationship data with keyboard-accessible controls and a list or table alternative to the graph, and SHALL bound graph payload and rendering size.

#### Scenario: Graph data exceeds the display limit
- **WHEN** available nodes or edges exceed the configured client limit
- **THEN** the API or UI applies explicit filtering/pagination, reports that the view is partial, and remains responsive

#### Scenario: Graph cannot be rendered
- **WHEN** canvas rendering is unsupported or disabled
- **THEN** the user can inspect the same relationships through an accessible list or table and open the corresponding note

### Requirement: Offline deterministic verification
The implementation SHALL provide offline deterministic tests for rendering, incremental planning, path containment, conflict preservation, atomic state behavior, API authentication, cancellation, and relationship provenance without requiring Obsidian, network access, or paid APIs.

#### Scenario: Offline quality suite runs
- **WHEN** the project quality command runs in an isolated test environment
- **THEN** Vault integration tests use temporary fixtures and complete without launching Obsidian or accessing external services
