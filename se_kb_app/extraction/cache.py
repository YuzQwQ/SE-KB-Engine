from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from se_kb_app.observability import METRICS


def extraction_cache_key(
    *,
    content_hash: str,
    model_version: str,
    prompt_version: str,
    schema_version: str,
    parameter_version: str,
) -> str:
    payload = json.dumps(
        {
            "content": content_hash,
            "model": model_version,
            "parameters": parameter_version,
            "prompt": prompt_version,
            "schema": schema_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def cache_is_compatible(metadata: Mapping[str, str], **versions: str) -> bool:
    compatible = all(metadata.get(name) == value for name, value in versions.items())
    METRICS.increment("cache_lookups_total", cache="extraction", outcome="hit" if compatible else "miss")
    return compatible
