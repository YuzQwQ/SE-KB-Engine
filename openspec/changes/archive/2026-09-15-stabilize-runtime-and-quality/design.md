## Context

The repository mixes several runtime surfaces and dependency declarations. The working tree already contains partial encoding, pytest, dependency, and `server.py` edits, so implementation must begin by verifying and preserving them rather than restarting. Later changes need a fast, deterministic baseline that works without secrets or external systems.

## Goals / Non-Goals

**Goals:** define one supported runtime matrix; make source UTF-8 and import-safe; make `pyproject.toml` authoritative; separate optional dependency groups; provide offline quality commands and isolated fixtures; prevent generated/runtime assets from contaminating checks.

**Non-Goals:** functional redesign, data cleanup, public contract changes, full coverage in one pass, or automated deletion of large tracked files.

## Decisions

1. Use `pyproject.toml` as the human-edited source and a generated lock/exports for reproducibility. Alternative: maintain three hand-edited requirement sets; rejected because they have already drifted.
2. Choose one Python support range after dependency compatibility probes, then use it consistently in Ruff, mypy, `.python-version`, CI, and Docker. Alternative: retain accidental 3.10–3.13 ambiguity; rejected because it cannot be tested honestly.
3. Default pytest to offline markers and make real network/model/browser/Tor suites explicit opt-ins. Alternative: mock globally without markers; rejected because accidental integration calls become hard to see.
4. Keep quality checks composable and expose one PowerShell-friendly orchestration command. Individual tools remain directly callable.
5. Treat existing uncommitted changes as candidate implementation: inspect, test, and amend in small diffs rather than overwrite.

## Risks / Trade-offs

- [A dependency does not support the selected Python] → record the probe, select the widest actually supported range, and isolate optional features.
- [Encoding conversion alters text] → compare decoded content and review diffs before replacement.
- [Stricter gates expose many failures] → record a baseline and ratchet by category; do not add blanket exclusions.
- [Repository hygiene suggests deletion] → report and propose migration; require separate approval for deletion/history changes.

## Migration Plan

Capture the current state; verify partial work; fix encoding/compile/import blockers; settle runtime/dependencies; add isolated tests and quality entrypoint; validate on Windows and container Linux. Roll back file-by-file; no data migration is involved.

## Open Questions

- Which Python minor range is supported by the chosen ChromaDB and MCP versions after clean-install probes?
- Should `cloudflared.exe` remain tracked, move to release assets, or be downloaded with a checksum?
