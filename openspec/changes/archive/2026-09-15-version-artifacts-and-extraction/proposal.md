## Why

Knowledge artifacts, schemas, prompts, refinement outputs, caches, and source evidence need explicit versions and provenance. Without atomic writes, stable identity, migration rules, and quality fixtures, interrupted or repeated runs can create ambiguous, duplicated, or unverifiable knowledge.

## What Changes

- Define a versioned artifact manifest linking source, content hash, cleaner, prompt, model, schema, validation, and derived files.
- Make writes atomic and detectable after interruption; add read-only integrity scanning and dry-run migration support.
- Establish deterministic cleaning and extraction fixtures covering multilingual text, code, tables, malformed HTML, and model-output failures.
- Add bounded model input/output handling, strict structured validation, traceable source anchors, caching, and explicit no-knowledge outcomes.
- Make refinement idempotent and preserve provenance/conflict decisions through deduplication and merging.

Non-goals: bulk-migrating the user's existing corpus during this change, deleting legacy artifacts, choosing a new model provider, or performing paid large-scale evaluations.

Prerequisites: `stabilize-runtime-and-quality` and the application seams from `modularize-application-core`; reliable jobs are recommended before bulk migration.

## Capabilities

### New Capabilities
- `versioned-artifacts`: Knowledge and intermediate artifacts have stable identity, provenance, atomic persistence, integrity checks, and reversible migration semantics.
- `trustworthy-extraction`: Cleaning, model extraction, validation, repair, caching, and refinement produce bounded and source-traceable outcomes.

### Modified Capabilities

None.

## Impact

Affects cleaners, extractors, validators, writers, refiner, schemas, prompts, caches, artifact directories, and migration/diagnostic tooling. Existing data is read-only until a separately approved migration run.
