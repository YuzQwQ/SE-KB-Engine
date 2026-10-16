## Context

Pipeline outputs span raw/parsed pages, artifacts, refined knowledge, caches, and vector inputs. The design must add integrity without assuming existing data is already conformant or safe to rewrite.

## Goals / Non-Goals

**Goals:** stable manifests/provenance; atomic storage; integrity scan and dry-run migration; bounded source-grounded extraction; idempotent refinement.

**Non-Goals:** automatic corpus migration/deletion, provider selection, or changing every historical document.

## Decisions

1. Add a versioned manifest with stable artifact/document IDs and content hashes; filenames remain human-readable labels, not identity.
2. Publish file sets via temporary paths and atomic replace, with manifest last as commit marker.
3. Readers support current and explicitly documented legacy versions; migrations are separate, dry-run first, and write to a new target.
4. Store source anchors and all processing versions in trace. Treat crawled/model text as untrusted data.
5. Make extraction outcomes a tagged result: success, no-knowledge, validation-failed, dependency-failed, or cancelled.
6. Cache keys include content, model, prompt, schema, and parameter versions.

## Risks / Trade-offs

- [More metadata increases storage] → keep bounded summaries/hashes and avoid duplicating full bodies.
- [Legacy diversity complicates readers] → inventory first and support only observed versions.
- [Atomic multi-file publication is imperfect] → manifest-last plus integrity scan detects incomplete batches.

## Migration Plan

Create schema and fixtures; implement new writer/reader; add integrity scan; dual-read legacy/new; validate dry-run migration on copies; require approval before corpus writes. Rollback retains legacy reader and original data.

## Open Questions

- Which historical artifact variants are still operationally required?
