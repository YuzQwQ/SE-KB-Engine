"""Deterministic HTML decoding without a model or remote encoding detector."""
from __future__ import annotations

import codecs
import re


def decode_payload(payload: bytes, content_type: str = "") -> tuple[str, str, float]:
    candidates = []
    if payload.startswith(codecs.BOM_UTF8):
        candidates.append("utf-8-sig")
    elif payload.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        candidates.append("utf-16")
    header = re.search(r"charset\s*=\s*[\"']?([^\s;\"']+)", content_type, re.I)
    if header:
        candidates.append(header.group(1))
    meta = re.search(br"charset\s*=\s*[\"']?([a-zA-Z0-9_-]+)", payload[:4096], re.I)
    if meta:
        candidates.append(meta.group(1).decode("ascii"))
    candidates.extend(["utf-8", "gb18030"])
    for encoding in dict.fromkeys(candidates):
        try:
            return payload.decode(encoding), encoding, 0.0
        except (LookupError, UnicodeError):
            continue
    content = payload.decode("utf-8", errors="replace")
    return content, "utf-8", content.count("\ufffd") / max(1, len(content))
