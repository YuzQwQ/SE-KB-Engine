## 1. Inventory and schemas

- [x] 1.1 Read-only inventory raw, parsed, artifact, refined, cache, and vector-input variants; report versions, corruption, duplicates, and consumers.
- [x] 1.2 Define versioned manifest, stable ID, processing trace, source anchor, derived-file, and tagged extraction-outcome schemas.
- [x] 1.3 Create fixtures for current and observed legacy variants plus incomplete, corrupt, duplicate, and orphan cases.

## 2. Atomic artifact lifecycle

- [x] 2.1 Implement stable content/document/artifact identity independent of display filenames with collision and repeat-run tests.
- [x] 2.2 Implement bounded path sanitization and temporary-write/fsync/atomic-replace helpers with failure-injection tests.
- [x] 2.3 Publish derived files first and the success manifest last; prove interrupted batches are not exposed as successful.
- [x] 2.4 Add dual-read support for new and explicitly supported legacy manifests without rewriting source data.
- [x] 2.5 Build a read-only integrity scanner that continues after errors and produces machine/human-readable reports.
- [x] 2.6 Build a copy-to-new-target migrator with dry-run, preflight, per-item results, post-validation, backup mapping, and rollback instructions.

## 3. Deterministic cleaning and context selection

- [x] 3.1 Assemble a licensed/desensitized fixture corpus for Chinese, English, mixed text, code, tables, lists, formulas, malformed HTML, and bad encodings.
- [x] 3.2 Define and measure body-retention, navigation-noise, metadata, structure, runtime, and memory baselines.
- [x] 3.3 Version cleaner rules and retain heading/source offsets needed to produce stable source anchors.
- [x] 3.4 Add safe input-size/token budgets and type-aware relevant-chunk selection instead of unbounded/full-page prompts.
- [x] 3.5 Delimit untrusted page text from instructions and add indirect-prompt-injection regression fixtures.

## 4. Structured extraction and refinement

- [x] 4.1 Record router, cleaner, prompt, model, parameter, schema, and application versions for every extraction attempt.
- [x] 4.2 Implement strict JSON/schema parsing for clean JSON, fenced JSON, harmless wrappers, truncation, invalid Unicode, and wrong shape.
- [x] 4.3 Add bounded repair attempts with complete validation diagnostics and no promotion after terminal validation failure.
- [x] 4.4 Distinguish success, no-knowledge, validation-failed, dependency-failed, policy-failed, and cancelled outcomes end to end.
- [x] 4.5 Include content/model/prompt/schema/parameter versions in cache keys and reject incompatible cached results.
- [x] 4.6 Make structural deduplication/refinement deterministic where possible and preserve all source/conflict decisions.
- [x] 4.7 Add repeat-run tests proving idempotency and provenance retention across writer, refiner, and merger.

## 5. Verification and controlled migration

- [x] 5.1 Run all new behavior against temporary corpus copies with fault injection and verify originals are byte-identical.
- [x] 5.2 Produce a dry-run migration report for the real corpus without writing to it; require separate approval before execution.
- [x] 5.3 Document artifact schema, lifecycle, outcomes, integrity scan, backup, migration, rollback, and data-retention responsibilities.
