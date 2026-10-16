# Artifact lifecycle and migration operations

This document defines the operational contract for versioned extraction artifacts. The
current manifest schema is `1.0`; its machine-readable definition is
`schemas/artifact-manifest-v1.schema.json`. Extraction outcomes are defined by
`schemas/extraction-outcome-v1.schema.json`.

## Schema and identity

Every committed batch has a `manifest.json` containing stable batch, document, and
content identities; the source URL; a creation timestamp; a complete processing trace;
an extraction outcome; derived-file hashes and byte sizes; optional source anchors; and
metadata. Content, document, and artifact IDs are derived from canonical inputs rather
than display filenames, so repeat runs produce the same identities.

The processing trace records the application, cleaner, router, prompt, model,
parameter, and output-schema versions. A source anchor records a document ID, character
range, quote hash, and optional heading path. Consumers must verify the declared schema
version and must not silently interpret an unknown version as version 1.

## Publication lifecycle

Writers sanitize and bound path components, write each file through a temporary file,
flush it, and atomically replace the destination. Derived files are published before
`manifest.json`; the manifest is the commit marker and is always published last. A
directory without a valid manifest is incomplete, even if it contains derived files.
Readers support schema 1.0 and only the explicitly observed legacy `metadata.json` and
`parsed.json` layouts. Reading legacy data never rewrites it.

## Extraction outcomes

The outcome tag is one of:

- `success`: validated artifacts were promoted and `artifact_ids` is non-empty.
- `no_knowledge`: processing completed but found no promotable knowledge.
- `validation_failed`: structured output remained invalid after bounded repair.
- `dependency_failed`: a required model, parser, storage, or other dependency failed.
- `policy_failed`: processing was rejected by a safety or trust policy.
- `cancelled`: the operation was cancelled before promotion.

Only `success` may contain promoted artifact IDs. Diagnostics remain attached to all
terminal outcomes so operators can distinguish empty results from failures.

## Integrity scans

Run a read-only human report with:

```powershell
.\.venv\Scripts\python.exe scripts\scan_artifacts.py <artifact-root>
```

Use `--json` for automation. The scanner continues after malformed files and reports
corrupt JSON, invalid manifests, missing derived files, size/hash mismatches, orphan
candidates, observed schema versions, and duplicate groups. A nonzero exit means an
integrity issue was found. Duplicate groups are review candidates and do not alone make
the report invalid. Scanning never repairs or deletes data.

## Controlled migration and backup

Migration is copy-only and always targets a different, absent or empty directory. Run
the mandatory dry-run first:

```powershell
.\.venv\Scripts\python.exe scripts\migrate_artifacts.py <legacy-root> <new-target>
```

Review all preflight errors, unsupported items, source-to-target backup mappings, and
planned batches. Record the report with the change or release evidence. `--execute`
must be used only after separate approval for that exact source and target:

```powershell
.\.venv\Scripts\python.exe scripts\migrate_artifacts.py <legacy-root> <new-target> --execute
```

Execution copies legacy payloads into versioned batches, preserves their origin in
manifest metadata, and runs a post-migration integrity scan. The legacy source remains
authoritative until the new target passes validation and its consumers are separately
switched over. A migration report is not authorization to change consumer paths.

Before execution, the operator must ensure the source is covered by the normal storage
backup policy and retain the dry-run report. The migration's `backup_mapping` is an
audit map, not a replacement for storage backups.

## Rollback

Before consumer cutover, rollback consists of removing or quarantining only the newly
created target and continuing to use the untouched source. After cutover, first point
consumers back to the source, verify reads, and then quarantine the target for forensic
review. Never modify or delete the legacy source as part of rollback. If source bytes
changed, stop and restore them through the owning storage backup procedure rather than
attempting an in-place repair.

## Data retention responsibilities

- The data owner defines retention periods, legal holds, access controls, and deletion
  approval for source material and derived artifacts.
- The migration operator preserves source bytes, records reports and mappings, and does
  not execute or delete data without approval for the exact paths.
- The application owner versions schemas and processing rules, maintains dual-read
  compatibility, and documents any end-of-support decision.
- The operations owner schedules integrity scans, investigates issues, monitors storage,
  and confirms backups and restoration procedures.
- Consumers retain provenance and source anchors when exporting, refining, caching, or
  indexing artifacts. Cache or vector deletion does not satisfy deletion of the source
  or committed artifacts; every governed copy must follow the data owner's policy.

Temporary files and failed, manifest-less batches may be quarantined only after an
integrity report and retention-policy check. Successful manifests, audit reports, and
backup mappings must be retained for at least as long as the artifacts they describe,
unless a stricter legal or organizational rule applies.
