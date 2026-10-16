## 1. Configuration and Contracts

- [x] 1.1 Add disabled-by-default Vault root, Vault name, managed directory, entity selection, semantic edge, and graph limit settings to the typed application configuration
- [x] 1.2 Validate configuration combinations and return redacted diagnostics for missing, inaccessible, or invalid Vault roots
- [x] 1.3 Define immutable domain models for Vault status, note identity, projected note, relationship edge, export action, export plan, and export result
- [x] 1.4 Define a versioned exporter-state schema with source and published hashes, logical paths, aliases, timestamps, and corpus fingerprint
- [x] 1.5 Add JSON schema or equivalent validation fixtures for accepted, unsupported-newer, malformed, and partially written exporter states
- [x] 1.6 Document the ownership boundary among versioned artifacts, the vector index, generated Vault notes, and user-authored notes

## 2. Path and Identity Safety

- [x] 2.1 Implement deterministic Unicode normalization and title sanitization for Windows and POSIX file names
- [x] 2.2 Handle Windows reserved device names, trailing dots/spaces, empty slugs, case-insensitive collisions, and configurable path-length limits
- [x] 2.3 Derive stable collision-resistant note suffixes from SE-KB identities and build a central identity-to-logical-path map
- [x] 2.4 Implement Vault and managed-root resolution with traversal, absolute-child, control-character, symlink, and reparse-point escape rejection
- [x] 2.5 Revalidate destination containment immediately before every temporary-file creation and atomic replacement
- [x] 2.6 Add table-driven offline tests covering Unicode titles, equivalent normalization forms, reserved names, collisions, long paths, traversal, and linked-directory escapes

## 3. Artifact Selection and Projection

- [x] 3.1 Add a read-only adapter that enumerates valid versioned source documents and curated entity artifacts through existing artifact readers
- [x] 3.2 Implement configurable selection by source, date, artifact kind, entity kind, and minimum quality without modifying corpus data
- [x] 3.3 Map source documents to one note each and preserve indexed chunks as deterministic heading or block anchors inside the parent note
- [x] 3.4 Map selected concepts, rules, patterns, examples, and other configured entities to standalone knowledge notes
- [x] 3.5 Preserve source URL, artifact/document identity, content hash, trace version, quality, note kind, aliases, and ownership marker in the projection model
- [x] 3.6 Add fixture tests proving raw chunks do not become standalone notes by default and source/entity selection remains deterministic

## 4. Markdown and Frontmatter Rendering

- [x] 4.1 Implement a deterministic UTF-8 frontmatter renderer with safe scalar, list, newline, delimiter, and Unicode quoting
- [x] 4.2 Implement Markdown rendering for source notes, entity notes, source attribution, generated links, anchored sections, and semantic suggestions
- [x] 4.3 Escape extracted titles, metadata, Markdown/wiki-link delimiters, HTML, and block identifiers so untrusted content cannot inject structure or executable markup
- [x] 4.4 Generate explicit wiki links exclusively from the completed identity-to-path map and emit an unresolved-reference diagnostic when a target is absent
- [x] 4.5 Preserve valid previous titles as aliases when an identity is renamed and prevent aliases from creating case-insensitive collisions
- [x] 4.6 Define which volatile run metadata is excluded from the content fingerprint so unchanged inputs remain byte-stable
- [x] 4.7 Add golden-file tests for multilingual content, malicious metadata, link escaping, aliases, anchors, and repeated byte-identical rendering

## 5. Relationship Projection

- [x] 5.1 Normalize explicit parent-child, source citation, dependency, cross-reference, and entity relationship records into a shared edge model
- [x] 5.2 Adapt retrieval similarity output into semantic edges with score, method, source index version, and provenance metadata
- [x] 5.3 Apply configurable similarity thresholds, maximum neighbors per node, deterministic tie-breaking, and duplicate-edge collapse
- [x] 5.4 Render explicit relationships and semantic suggestions in visually and semantically distinct note sections
- [x] 5.5 Add a bounded relationship query service supporting kind, source, node, score, and pagination filters
- [x] 5.6 Add offline tests showing semantic suggestions are never mislabeled as explicit facts and oversized graphs are predictably bounded

## 6. Export Planning and State

- [x] 6.1 Implement exporter-state loading with schema-version checks, integrity diagnostics, and read-only failure for unsupported newer versions
- [x] 6.2 Compute a deterministic corpus/configuration fingerprint and per-note source/content fingerprints
- [x] 6.3 Build an export planner that classifies create, update, rename, unchanged, conflict, skipped, and stale actions before any write
- [x] 6.4 Detect user modifications by comparing current file hashes with the last exporter-owned published hashes
- [x] 6.5 Treat unrecorded files occupying planned destinations as conflicts and preserve them byte-for-byte
- [x] 6.6 Keep stale notes by default and include them in preview/result summaries without scheduling a destructive action
- [x] 6.7 Bound preview detail while preserving total counts and stable pagination for large plans
- [x] 6.8 Add incremental-plan tests for first export, unchanged export, content update, title rename, user conflict, unknown collision, stale notes, and lost state

## 7. Atomic Publication and Recovery

- [x] 7.1 Implement a per-managed-root writer lock that prevents interleaved publication and reports a clear busy result
- [x] 7.2 Write planned content to uniquely named temporary files inside the managed root and verify bytes and hashes before replacement
- [x] 7.3 Atomically replace eligible targets where supported and commit exporter state only after all planned note operations verify
- [x] 7.4 Insert cancellation checkpoints before rendering batches, before replacements, and before state commit using the existing cancellation abstraction
- [x] 7.5 Detect and safely clean exporter-owned abandoned temporary files on a later run without touching unknown files
- [x] 7.6 Produce a structured publication result containing action counts, conflicts, skips, diagnostics, logical paths, and final fingerprint
- [x] 7.7 Add fault-injection tests for render failure, temporary write failure, replacement failure, state-commit failure, cancellation, and concurrent writers
- [x] 7.8 Verify every failure path preserves unowned files and never records a partial projection as successfully published

## 8. Application Composition and Managed Jobs

- [x] 8.1 Add Vault planner, renderer, relationship provider, state store, and publisher interfaces at the application boundary
- [x] 8.2 Compose filesystem and retrieval adapters through the existing settings/factory pattern without initializing them when integration is disabled
- [x] 8.3 Add a synchronous bounded status service and dry-run preview service with consistent application-error mapping
- [x] 8.4 Add a managed export operation that reports stage progress and result references through the existing job store and runner
- [x] 8.5 Ensure application shutdown releases Vault writer locks and closes any relationship/retrieval adapters without affecting existing services
- [x] 8.6 Add composition and managed-job tests for disabled, unavailable, preview, successful, failed, cancelled, and busy states

## 9. Authenticated REST API

- [x] 9.1 Define additive response contracts for Vault status, export preview, export submission, relationship queries, and note location
- [x] 9.2 Add an authenticated read-only Vault status endpoint with redacted diagnostics and no unrelated absolute host paths
- [x] 9.3 Add an authenticated preview endpoint with validated selection/filter input, categorized counts, and paginated details
- [x] 9.4 Add an authenticated export endpoint returning the standard job identifier, location header, and accepted status
- [x] 9.5 Reuse the existing job status and cancellation endpoints for Vault export progress and terminal results
- [x] 9.6 Add an authenticated bounded relationship endpoint with validation for node, kind, score, offset, and limit parameters
- [x] 9.7 Add an authenticated note-location endpoint returning an encoded `obsidian://open` URI and Vault-relative fallback path without launching a process
- [x] 9.8 Add REST contract tests for authentication failures, invalid configuration/input, unavailable Vault, preview, job submission, cancellation, pagination, URI encoding, and error redaction

## 10. Web Console Workspace

- [x] 10.1 Add a Knowledge Map/Vault navigation tab without changing existing acquisition, refinement, or semantic-search DOM/API contracts
- [x] 10.2 Build Vault summary cards for configuration state, managed-note totals, conflicts, stale notes, last export, and source fingerprint
- [x] 10.3 Build export selection and dry-run controls with clear disabled/unavailable states and inline validation
- [x] 10.4 Build a categorized preview/results table showing logical path, note kind, action, reason, and an accessible details view
- [x] 10.5 Connect publication to existing job polling, progress, cancellation, logs, and terminal-state patterns
- [x] 10.6 Implement a bounded two-dimensional relationship graph with explicit and semantic edge styling, filters, selection, and partial-view disclosure
- [x] 10.7 Provide a keyboard-accessible relationship list/table containing the same nodes, edges, scores, provenance, and note actions as the graph
- [x] 10.8 Add “Open in Obsidian” and copy-relative-path actions with graceful fallback when the custom URI is unsupported
- [x] 10.9 Ensure graph labels, note content, API errors, and paths are inserted as text rather than trusted HTML
- [x] 10.10 Add responsive layouts, visible focus states, reduced-motion behavior, empty/loading/error states, and narrow-screen graph fallbacks

## 11. Optional Canvas Projection

- [x] 11.1 Confirm the target Obsidian Canvas schema and record the supported subset and compatibility assumptions in project documentation
- [x] 11.2 Implement deterministic Canvas generation from bounded relationship data behind a disabled-by-default option
- [x] 11.3 Use stable node/edge identifiers, Vault-relative note links, explicit-versus-semantic styling, and collision-free placement
- [x] 11.4 Treat existing divergent Canvas files as conflicts and include them in the same preview and ownership model as notes
- [x] 11.5 Add golden fixtures validating Canvas JSON structure, stable layout, escaping, relationship provenance, and disabled behavior

## 12. Documentation and End-to-End Verification

- [x] 12.1 Document configuration, Vault preparation, managed-directory ownership, preview/export workflow, conflict recovery, and rollback
- [x] 12.2 Document privacy and security implications of exposing source metadata and semantic relations inside a Vault
- [x] 12.3 Document that Obsidian, network access, community plugins, and paid models are not required for export or default tests
- [x] 12.4 Add an offline end-to-end fixture that exports a multilingual mini-corpus, verifies notes/links/state, repeats unchanged, introduces a conflict, and verifies preservation
- [x] 12.5 Add browser tests for configured and unconfigured workspaces, preview, export progress, graph/list parity, keyboard navigation, and mobile layout
- [x] 12.6 Run targeted Vault unit, service, API, and browser tests and record the commands and results
- [x] 12.7 Run the full project quality command, type checks, lint, compile checks, security checks, and deterministic offline test suite
- [x] 12.8 Validate the OpenSpec change and reconcile any implementation discoveries back into proposal, design, specs, and tasks before archival
