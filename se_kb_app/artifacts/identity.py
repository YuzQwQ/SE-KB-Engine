from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from typing import Any


def content_id(content: str | bytes) -> str:
    payload = content.encode("utf-8") if isinstance(content, str) else content
    return f"cnt_{hashlib.sha256(payload).hexdigest()}"


def document_id(source_url: str, content_hash: str) -> str:
    return _stable_id("doc", {"source_url": source_url.strip(), "content_hash": content_hash})


def artifact_id(document_identifier: str, artifact_type: str, payload: Mapping[str, Any]) -> str:
    return _stable_id(
        "art",
        {
            "document_id": document_identifier,
            "artifact_type": artifact_type,
            "payload": payload,
        },
    )


def _stable_id(namespace: str, value: Mapping[str, Any]) -> str:
    normalized = _normalize(value)
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"{namespace}_{hashlib.sha256(encoded).hexdigest()}"


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value
