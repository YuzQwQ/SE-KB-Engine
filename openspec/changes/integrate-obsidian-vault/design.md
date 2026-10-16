## Context

SE-KB stores versioned source material and generated knowledge artifacts, including Markdown, stable document/artifact IDs, content hashes, source URLs, heading anchors, metadata, and retrieval records. Obsidian operates on a directory of Markdown notes and derives backlinks and graph views from wiki links and metadata. The integration therefore does not need a second knowledge database; it needs a safe projection boundary between authoritative SE-KB data and a user-owned Vault.

The integration crosses storage, application services, authenticated REST routes, managed jobs, configuration, and the Web console. It must work on Windows development hosts and Linux containers, remain deterministic offline, and never assume that Obsidian is installed or running.

## Goals / Non-Goals

**Goals:**

- Produce an idempotent, inspectable Obsidian projection from selected valid SE-KB artifacts.
- Preserve stable note identity and links when display titles change.
- Separate system-managed notes from user-owned Vault content.
- Preview every export, report conflicts, and publish changed files atomically.
- Expose status, export progress, relationships, and Obsidian deep links through existing authenticated surfaces.
- Distinguish durable, explicit knowledge relations from approximate semantic suggestions.
- Support cancellation, incremental rebuilds, and deterministic offline tests.

**Non-Goals:**

- Treating the Vault or vector store as a replacement for versioned artifacts.
- Bidirectional synchronization of note bodies or arbitrary user edits.
- Building or distributing an Obsidian plugin.
- Starting the Obsidian desktop process from the server.
- Exporting every retrieval chunk as a standalone note.
- Automatically deleting stale or conflicted files.
- Requiring network access, a paid model, Dataview, or another community plugin.

## Decisions

### 1. Model the Vault as a projection, not a second source of truth

Versioned artifacts remain authoritative. The vector index and Obsidian Vault are independently rebuildable projections. The export service reads through the existing artifact reader and never mutates source artifacts or vector data.

Alternative considered: make Obsidian the canonical store. This would weaken current manifests, hashes, processing trace, and reproducibility, and would create ambiguous ownership of generated content.

### 2. Isolate generated content in a managed namespace

The configured Vault root contains a configurable managed directory, defaulting to `SE-KB/`. Only files recorded in the export state manifest and resolving beneath that managed directory are eligible for update. User-authored directories are never scanned for rewriting or cleanup.

Generated notes carry machine-readable frontmatter including schema version, SE-KB identity, source identity, content hash, note kind, generation timestamp, and ownership marker. Human annotations belong outside the generated region in this phase.

Alternative considered: mix generated files into existing topic folders. That improves visual organization but makes ownership, collision handling, and rollback unsafe.

### 3. Use stable identity in file names and readable titles in note content

Each generated file name combines a sanitized readable slug with a short suffix derived from the stable SE-KB identity. Wiki links are produced from the exporter’s identity-to-path map, not guessed from titles. A title change can create a planned rename while retaining aliases in frontmatter. Reserved Windows names, Unicode normalization, case-insensitive collisions, and path-length limits are handled deterministically.

Alternative considered: title-only file names. They are pleasant initially but unstable and collision-prone.

### 4. Export documents and curated knowledge entities, not raw chunks

Source documents become source notes. Extracted concepts, rules, patterns, examples, and other curated entities can become knowledge notes when they meet configured quality/selection rules. Retrieval chunks remain addressable through headings or block anchors within their parent note. This keeps the graph meaningful and bounded.

### 5. Separate explicit links from semantic suggestions

Explicit artifact relationships, source citations, parent-child links, and cross-references are rendered as durable wiki links. Vector similarity produces a bounded `Semantic suggestions` section and relationship edges carrying score and algorithm metadata. Suggested edges are never represented as asserted facts and can be disabled or rebuilt independently.

### 6. Plan first, then publish atomically

Every export builds an in-memory plan containing creates, updates, renames, unchanged files, conflicts, skips, and stale candidates. Dry-run returns the same plan without writes. A real export writes temporary files in the managed directory, fsyncs where supported, then replaces targets atomically. The state manifest is committed last. Cancellation before manifest commit leaves the previous valid state authoritative; temporary files are cleaned on the next run.

Files whose current hash differs from the last exporter-owned hash are conflicts and are not overwritten unless a future explicit force policy is introduced. Stale notes are reported and retained by default.

Alternative considered: directly rewrite files during traversal. It is simpler but exposes partially updated graphs and makes rollback unreliable.

### 7. Enforce path containment at every filesystem boundary

Both Vault root and managed root are resolved before use. Relative paths, traversal, absolute child paths, control characters, symlink/reparse-point escapes, and writes outside the resolved managed root are rejected. Configuration and export endpoints remain protected by the existing service authentication policy. API responses expose logical note paths, not unrelated host filesystem contents.

### 8. Reuse managed jobs for export execution

Preview and status reads are synchronous and bounded. Publication runs through the existing managed-job infrastructure so progress, cancellation, terminal state, and error behavior stay consistent with crawl and refine operations. A single Vault export lock prevents interleaved publication to the same managed root.

### 9. Keep REST and UI contracts additive

Add authenticated endpoints for configuration/status, preview, export job submission, relationship data, and deep-link construction. The server returns a URL-encoded `obsidian://open` URI; the browser/user initiates it. Existing endpoints and page workflows remain unchanged.

The Web console adds a Knowledge Map/Vault workspace with summary cards, plan/result tables, filters, a bounded graph, and accessible list/table fallbacks. Large relationship sets are paginated or capped before browser rendering.

### 10. Use a versioned exporter state schema

The state manifest records exporter schema version, Vault identity, managed root, last successful export, source corpus fingerprint, and per-note logical path/source hash/published hash. Unknown newer state versions fail safely in read-only mode. The first implementation does not require migration of artifacts or vector stores.

## Risks / Trade-offs

- **User edits a generated note** → Detect divergence from the last published hash, classify it as a conflict, and preserve the file.
- **Vault path points at an unintended directory** → Require explicit configuration, resolved containment checks, preview, and an ownership marker before publication.
- **Symlink or Windows reparse point escapes the managed root** → Reject traversed output parents and verify the resolved destination immediately before replacement.
- **Title changes break links** → Build links from stable identities, plan renames centrally, and retain prior titles as aliases.
- **Semantic edges overwhelm the graph** → Cap neighbors per node, require a minimum score, label suggestions, and allow disabling them.
- **Very large exports block the Web process** → Use managed jobs, incremental hashes, bounded API payloads, cancellation checkpoints, and one-writer locking.
- **Obsidian URI behavior varies by host** → Return the URI without launching a process and retain copyable Vault-relative paths as fallback.
- **YAML/Markdown injection from extracted content** → Use deterministic escaping/quoting and render untrusted values as data rather than raw frontmatter or HTML.
- **Projection state is lost** → Reconstruct a preview from frontmatter and source identities; never infer permission to overwrite divergent notes.
- **Container cannot access a desktop Vault** → Report an unavailable/misconfigured status; exporting remains optional and does not degrade acquisition or retrieval.

## Migration Plan

1. Add disabled-by-default configuration and pure planning/rendering components.
2. Add offline tests with temporary Vault fixtures across Windows-sensitive and POSIX path cases.
3. Add the exporter state schema, dry-run CLI/service path, and integrity checks.
4. Add managed publication and authenticated API endpoints.
5. Add Web console controls and graph/list visualization behind the configured-state check.
6. Enable a user-selected Vault only after a successful preview; the initial export creates only the managed namespace.
7. Roll back by disabling the integration and reverting application code. Existing Vault files remain intact; users may remove the clearly marked managed directory after reviewing it.

## Open Questions

- Whether the default visible managed directory should be `SE-KB/` or a user-selected folder during onboarding.
- Whether Obsidian Canvas output belongs in the initial delivery or immediately after the graph dataset and UI are stable.
- Which extracted entity kinds meet the default quality threshold for standalone notes; the implementation should make this configurable without changing the state schema.

