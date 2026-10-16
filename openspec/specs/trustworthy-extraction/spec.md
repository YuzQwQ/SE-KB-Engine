# Trustworthy extraction

## Purpose

Define bounded, validated, source-traceable, and repeatable extraction and refinement behavior for untrusted crawled content.

## Requirements

### Requirement: Bounded and untrusted model context
Crawled content SHALL be treated as untrusted data, delimited from system instructions, and selected under configured input/output token and size budgets.

#### Scenario: Embedded prompt instruction
- **WHEN** a page asks the model to ignore extraction instructions or reveal secrets
- **THEN** the content remains data and no secret or unrelated tool action is produced

### Requirement: Strict structured outcome
Model output SHALL be parsed and validated against the selected schema with bounded repair attempts and an explicit final outcome.

#### Scenario: Invalid model JSON
- **WHEN** all allowed repairs still fail schema validation
- **THEN** the result is validation-failed with safe diagnostics and is not promoted to formal knowledge

### Requirement: Source traceability
Extracted claims SHALL retain document and source-span anchors plus cleaner, router, prompt, model, parameter, and schema versions.

#### Scenario: Reviewed knowledge item
- **WHEN** a reviewer inspects an extracted item
- **THEN** they can locate the supporting source fragment and processing trace

### Requirement: Idempotent refinement
Repeating refinement on identical inputs and configuration SHALL not duplicate knowledge, lose provenance, or change output nondeterministically without a recorded model source of variation.

#### Scenario: Repeated deterministic refinement
- **WHEN** the same validated artifact set is refined twice with deterministic components
- **THEN** stable IDs, merged content, conflicts, and provenance are equivalent
