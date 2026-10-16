# Obsidian Vault integration verification

Verification date: 2026-09-18

## Automated checks

```powershell
uv run pytest -q tests/test_obsidian_foundations.py tests/test_obsidian_projection.py tests/test_obsidian_relationships.py tests/test_obsidian_export.py tests/test_obsidian_service.py tests/test_obsidian_api.py tests/test_obsidian_canvas.py tests/test_obsidian_e2e.py
```

Result: `52 passed, 1 skipped`. The skipped case is the linked-directory escape test on a Windows environment that does not grant symlink creation privileges.

```powershell
uv run mypy .
```

Result: no issues in 221 source files.

```powershell
uv run python scripts/quality.py
```

The final successful run covers encoding and compile checks, dependency drift, the offline security scan, delivery configuration, documentation links, Ruff, mypy, the deterministic retrieval benchmark, and the full offline pytest suite.

```powershell
openspec validate integrate-obsidian-vault --strict
```

Result: the change is valid.

## Browser acceptance

The local console was exercised against an isolated multilingual corpus and Vault using a real browser at desktop and 390 x 844 mobile sizes.

- The configured workspace reported `available`, the correct Vault name, and three managed notes after export.
- A separately started unconfigured workspace reported `尚未配置`, explained how to enable the integration, and kept preview, export, and graph actions disabled.
- Dry-run preview reported three creates before export and three unchanged notes after export.
- The relationship graph and its accessible table represented the same three explicit relationships across three nodes.
- Left and right arrow keys moved focus and selection between the Semantic Search and Knowledge Map tabs.
- The narrow layout had no page-level horizontal overflow; the wide graph remained locally scrollable and the relationship table remained available.
- No browser console warnings or errors were recorded.

The automated API suite separately covers disabled and unavailable configurations, validation, authentication, cancellation, pagination, URI encoding, and diagnostic redaction.
