# Versioned artifacts

## Purpose

Define traceable, atomic, inspectable, and reversibly migratable artifact storage across current and explicitly supported legacy formats.

## Requirements

### Requirement: Versioned artifact manifest
Every newly published artifact batch SHALL have a manifest containing schema version, stable IDs, source identity, content hashes, processing versions, derived-file references, timestamps, and outcome.

#### Scenario: Complete publication
- **WHEN** an artifact batch is published successfully
- **THEN** every referenced file exists, matches its recorded hash, and is reachable from the manifest

### Requirement: Atomic publication
The system SHALL NOT expose a partially written batch as successful and SHALL preserve the prior valid state if publication fails.

#### Scenario: Failure before manifest commit
- **WHEN** the process fails during derived-file writing
- **THEN** no success manifest points to the partial files and the previous batch remains readable

### Requirement: Read-only integrity scan
Operators SHALL be able to scan current and supported legacy artifacts for version, missing files, hash mismatch, truncation, duplication, and orphan candidates without modifying data.

#### Scenario: Corrupt JSON
- **WHEN** a truncated artifact is scanned
- **THEN** the report identifies its path, manifest relationship, and error while continuing the scan

### Requirement: Reversible migration
Format migration SHALL support dry-run, source backup/copy, per-item results, validation, and rollback without overwriting the only source copy.

#### Scenario: Dry-run migration
- **WHEN** an operator requests dry-run
- **THEN** the system reports planned reads, writes, conflicts, and unsupported records while writing no corpus data
