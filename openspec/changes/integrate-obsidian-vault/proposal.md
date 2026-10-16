## Why

SE-KB already produces traceable Markdown documents, stable artifact identifiers, anchors, metadata, and semantic relationships, but users cannot browse or curate that knowledge through the Obsidian workflows they already use. A safe Obsidian projection would make the corpus navigable as notes and links while preserving SE-KB as the authoritative, versioned source and the vector index as a rebuildable retrieval layer.

## What Changes

- Add a configurable, one-way exporter that projects selected SE-KB documents and extracted knowledge into an Obsidian-compatible Vault directory.
- Generate deterministic Markdown notes with YAML frontmatter, stable note identities, source attribution, heading/block anchors, and explicit wiki links.
- Keep generated content in a managed namespace and publish atomically so interrupted exports do not corrupt an existing Vault projection.
- Track export state and report created, updated, unchanged, conflicted, skipped, and stale notes without deleting user data by default.
- Expose Vault status, export controls, note relationships, and an “Open in Obsidian” action through the existing Web/API surfaces.
- Generate a lightweight relationship dataset suitable for an in-app graph and optionally an Obsidian Canvas, while distinguishing explicit links from semantic suggestions.
- Add offline, deterministic validation and tests for path safety, stable output, escaping, conflict handling, and incremental export.
- Treat bidirectional body synchronization, automatic rewriting of user-authored notes, Obsidian plugin development, and bulk deletion of stale notes as explicit non-goals for this phase.
- Require a valid, user-selected Vault root and existing versioned artifact reader/index inputs; exporting must not require network access, a paid API, or a running Obsidian process.

## Capabilities

### New Capabilities

- `obsidian-vault-integration`: Safely project versioned SE-KB knowledge into an Obsidian Vault, expose export/status/open-note operations, and provide explicit and semantic relationship data for visualization.

### Modified Capabilities

None. The change consumes existing versioned artifacts and retrieval output without changing their public requirements.

## Impact

- New application service and adapters for Vault planning, Markdown rendering, state tracking, atomic publication, URI generation, and relationship projection.
- New authenticated REST endpoints plus Web console controls and visualization components.
- Configuration additions for Vault root, managed subdirectory, export selection, Canvas generation, and safe stale-note policy.
- Tests and documentation covering Windows paths, Linux containers, Unicode titles, note-name collisions, symlinks/reparse points, and user-modified generated files.
- No corpus migration is required. Existing artifacts and vector stores remain untouched, external network and paid APIs are not introduced, and destructive cleanup remains opt-in with a dry-run preview.
