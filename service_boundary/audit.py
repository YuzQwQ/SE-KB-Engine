from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable
from se_kb_app.observability import redact_text

AUDIT_LOGGER = logging.getLogger("se-kb.audit")
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


def redact(value: object, secrets: Iterable[str] = ()) -> str:
    secret_values = tuple(secrets)
    marker = "__SE_KB_REDACTED_BEARER__"
    text = BEARER_PATTERN.sub(marker, str(value))
    text = redact_text(text, secret_values).replace(marker, "Bearer [REDACTED]")
    for secret in secret_values:
        if secret:
            text = text.replace(secret, "[REDACTED]")
            if len(secret) >= 8:
                text = text.replace(secret[:8], "[REDACTED-PREFIX]")
    return text


def configured_secrets() -> tuple[str, ...]:
    values: list[str] = []
    for name in (
        "OPENAI_API_KEY",
        "FILTER_API_KEY",
        "KB_API_KEY",
        "KB_READ_KEYS",
        "KB_ADMIN_KEYS",
        "SERPAPI_API_KEY",
        "TOR_PASSWORD",
    ):
        values.extend(part.strip() for part in os.getenv(name, "").split(",") if part.strip())
    return tuple(values)


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage(), configured_secrets())
        record.args = ()
        return True


def install_secret_redaction() -> None:
    root = logging.getLogger()
    if not any(isinstance(item, SecretRedactionFilter) for item in root.filters):
        root.addFilter(SecretRedactionFilter())
    for handler in root.handlers:
        if not any(isinstance(item, SecretRedactionFilter) for item in handler.filters):
            handler.addFilter(SecretRedactionFilter())


def audit_event(event: str, outcome: str, correlation_id: str, **fields: object) -> None:
    safe_fields = " ".join(
        f"{key}={redact(value)}" for key, value in sorted(fields.items()) if value is not None
    )
    AUDIT_LOGGER.info(
        "event=%s outcome=%s correlation_id=%s%s",
        event,
        outcome,
        correlation_id,
        f" {safe_fields}" if safe_fields else "",
    )
