## 1. Preserve and measure the current state

- [x] 1.1 Record Git status, runtime/tool versions, current quality-command results, tracked large files, and disk-heavy ignored paths in a timestamped baseline report.
- [x] 1.2 Review the existing uncommitted `server.py`, dependency, encoding-script, pytest, and fixture changes; map each hunk to this change without overwriting unrelated work.
- [x] 1.3 Add regression coverage that reproduces every confirmed compile, import, and dependency-declaration failure before further fixes.

## 2. Normalize source and runtime

- [x] 2.1 Complete a read-only UTF-8/compile scanner with tests for UTF-8, BOM, UTF-16, invalid bytes, exclusions, and non-mutating failure behavior.
- [x] 2.2 Convert each confirmed formal non-UTF-8 file independently, review semantic diffs, and make all supported Python sources pass `compileall`.
- [x] 2.3 Probe core and optional dependencies on candidate Python versions, document the evidence, and select the supported range.
- [x] 2.4 Align `requires-python`, Ruff, mypy, `.python-version`, local documentation, CI intent, and Docker intent to the selected range.

## 3. Make dependencies reproducible

- [x] 3.1 Inventory imported packages and reconcile `pyproject.toml`, `requirements.txt`, `requirements-prod.txt`, and `uv.lock` conflicts.
- [x] 3.2 Move runtime, development, crawl/browser, vision, API, and vector dependencies into explicit authoritative groups.
- [x] 3.3 Generate the lock and any production export from the authoritative declaration and add a drift check.
- [x] 3.4 Verify a clean core install and at least one production/container install without using private credentials.

## 4. Build the offline safety net

- [x] 4.1 Finish pytest markers and fixtures for temporary data roots, isolated environment, stable time/randomness, and fake HTTP/model clients.
- [x] 4.2 Add smoke-import tests for formal packages and entry-point factories with secrets removed and outbound network blocked.
- [x] 4.3 Classify `scripts/test_*.py` as manual diagnostics, opt-in integration tests, or migrated pytest tests, and prevent import-time execution.
- [x] 4.4 Add representative unit tests for environment loading, URL normalization/deduplication, HTML cleaning, chunking, schema validation, and type registration.
- [x] 4.5 Add a fast aggregate quality command that runs encoding/compile, Ruff, mypy, and offline pytest while preserving non-zero failures.

## 5. Repository safeguards and verification

- [x] 5.1 Add `.gitattributes` and `.editorconfig` for UTF-8/text normalization without mass-reformatting unrelated files.
- [x] 5.2 Audit `.gitignore` coverage for secrets, logs, caches, browser/Tor state, output, raw data, and vector stores; add only proven missing patterns.
- [x] 5.3 Document tracked `cloudflared.exe` and `web_cache.db` options and risks; do not delete or rewrite history without approval.
- [x] 5.4 Run the aggregate quality gate twice from clean temporary state and record deterministic results, known scoped debt, and exact follow-up owners.
- [x] 5.5 Update setup/testing documentation with supported Python, dependency groups, offline defaults, and opt-in external markers.
