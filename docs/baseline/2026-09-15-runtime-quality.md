# Runtime and quality baseline — 2026-09-15

## Scope and working-tree safety

- Change: `stabilize-runtime-and-quality`
- Repository had pre-existing modifications to `pyproject.toml`, `requirements.txt`, and `server.py` plus untracked tests, encoding tooling, generated copyright material, and output data.
- This change treats all pre-existing files as user work. Generated documents, `output/`, real data, logs, vector stores, and credentials are outside the write scope.
- `server.py` already removed a duplicated/corrupt 59-line fragment. The removal is retained and verified by compile/import/tool-list regression tests.
- `requirements.txt` had already been mechanically converted from UTF-16 content into a UTF-8 environment freeze; it is not yet an authoritative project dependency declaration.

## Environment

- Windows / PowerShell workspace
- Python launchers: 3.13.2 and 3.11 available
- Active project environment: Python 3.13.2
- pip 25.1.1; uv 0.6.12
- pytest 8.3.5; Ruff 0.15.2; mypy 1.19.1
- Project metadata initially declared Python `>=3.13`; Docker initially used Python 3.10.

## Initial measurements

- Encoding scan inspected 387 candidate text files and reported `old_format_files.txt` as UTF-16. That file is a generated historical inventory, not formal source, and is now excluded explicitly rather than rewritten.
- Initial pytest: 1 passed, 4 failed. Three failures were caused by the Windows parent process decoding UTF-8 child output as GBK; one exposed `web.app` importing `services` as a nonexistent top-level module.
- Initial Ruff: one unused import in an untracked generated copyright script outside this change.
- Initial mypy: errors were confined to untracked copyright-generation scripts and the initial encoding checker; the generated scripts are outside this change.
- Tracked large/source-risk items include `cloudflared.exe` (~68 MB), `web_cache.db`, and `server.py` (~114 KB).
- Ignored disk-heavy paths include local virtual environments, logs, Tor state, raw crawl data, output documents, and `se_kb` runtime/artifact/index data.

## Confirmed regression targets

1. Formal text must be valid UTF-8 and formal Python must compile without writing `.pyc` files into user/runtime directories.
2. Tests must include their own source in encoding checks and exclude only named runtime/generated paths.
3. Smoke subprocess output must decode deterministically as UTF-8 on Windows.
4. `web.app` must use a package-qualified services import.
5. MCP server import and tool registration must succeed offline after removal of the corrupt duplicate fragment.
6. Dependency declarations must be generated from `pyproject.toml`, not from an arbitrary developer-environment freeze.

## Initial commands

```powershell
.\.venv\Scripts\python.exe scripts\check_encodings.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy . --no-error-summary
```

This file records evidence, not acceptance. Final repeat-run results are added when the aggregate quality gate exists.

## Final verification

The aggregate command is `scripts/quality.ps1` (portable implementation:
`python scripts/quality.py`). It sets UTF-8 subprocess output, disables bytecode writes and dotenv
loading, preserves each child process's non-zero status, and runs the following checks in order:

1. read-only UTF-8 and Python compile scan;
2. lock/export dependency drift check;
3. Ruff;
4. mypy;
5. pytest with the default outbound-network blocker and temporary data roots.

The first aggregate attempt correctly failed because a positive dotenv-loading test inherited the
gate's `SE_KB_SKIP_DOTENV=1`. The test now clears that variable explicitly, making its precondition
independent of the caller.

Two subsequent runs from fresh pytest temporary directories produced identical acceptance results:

| Run | Encoding/compile | Dependencies | Ruff | mypy | Offline pytest |
| --- | --- | --- | --- | --- | --- |
| 1 | 390 files / 93 Python, pass | consistent | pass | pass | 24 passed (15.62 s) |
| 2 | 390 files / 93 Python, pass | consistent | pass | pass | 24 passed (15.65 s) |

Clean-install probes also passed on both supported range boundaries: Python 3.11.8 with the
production API export and Python 3.13.2 with the all-extras export. No credentials or external
service calls were used.

## Scoped debt and follow-up ownership

- mypy emits informational notes for untyped function bodies in `client.py`,
  `extractors/type_registry.py`, and a test fixture; stronger application typing belongs to
  `modularize-application-core`.
- The entire ignored `se_kb/` tree currently mixes runtime state with source-like content. Its
  separation and artifact migration belong to `version-artifacts-and-extraction`; nothing was
  deleted in this change.
- CI boundary-version jobs and container/release enforcement belong to
  `productionize-observability-and-delivery`; this change records the intended Python 3.11/3.13
  matrix and aligns the Docker baseline.
- `cloudflared.exe` and `web_cache.db` remain tracked pending a maintainer decision documented in
  `docs/REPOSITORY_ASSETS.md`; history rewriting remains explicitly out of scope.
- Local clean-install probe environments were created only under ignored `.tmp/`. Automated
  workspace policy prevented their recursive removal, so `.tmp/dependency-probe-py311` and
  `.tmp/dependency-probe-py313` may be removed manually; neither is scanned, tracked, or used by
  the quality gate.
