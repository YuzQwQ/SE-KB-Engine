# Testing and quality checks

## Default offline gate

The required local gate is deterministic and offline by default:

```powershell
.\scripts\quality.ps1
```

The cross-platform equivalent is:

```bash
python scripts/quality.py
```

It checks UTF-8/compilation, dependency drift, Ruff, mypy, and pytest. Tests isolate project environment variables, use temporary data roots, and block external sockets unless the test has an explicit external marker.

## Test markers

`pytest` runs `unit` and local `integration` tests by default. The following suites require explicit selection and appropriate local setup:

- `network`: public network access
- `llm`: a real, potentially paid model API
- `browser`: installed Playwright browser binaries
- `tor`: a local Tor process
- `docker`: Docker engine
- `slow`: longer than 30 seconds

Example opt-in invocation:

```powershell
python -m pytest --override-ini="addopts=" -m network
```

Never place real credentials or private model responses in test fixtures, snapshots, or failure output.

## Existing manual diagnostic scripts

The historical `scripts/test_*.py` files are guarded command-line diagnostics, not collected pytest tests. All currently have `if __name__ == "__main__"` guards.

| Scripts | Classification | External requirements |
| --- | --- | --- |
| `test_decompose.py`, `test_pipeline.py`, `test_preselector.py` | Manual pipeline integration diagnostics | Local sample data; some modes use an LLM |
| `test_embedding.py`, `test_vector_store.py` | Manual vector integration diagnostics | Embedding API and/or local vector data |
| `test_llm_connection.py`, `test_merger_api.py` | Manual paid-service diagnostics | LLM credentials and network |
| `test_crawl_single.py` | Manual crawler diagnostic | Network; optional browser/vision model |
| `test_vision_from_parsed.py`, `test_vision_run.py`, `test_vision_single.py` | Manual vision diagnostics | Image fixtures and model credentials |

New deterministic behavior belongs in `tests/`. External scripts should gradually become explicitly marked pytest integration tests when they can isolate inputs and redact outputs.
