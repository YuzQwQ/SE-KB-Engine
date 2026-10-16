from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Mapping

CORRELATION_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


@dataclass
class PublicError(Exception):
    code: str
    message: str
    status: int
    field: str | None = None

    def __str__(self) -> str:
        return self.code


ERROR_CATALOG: Mapping[str, tuple[int, str]] = {
    "invalid_request": (400, "The request is invalid."),
    "invalid_field": (400, "A request field is invalid."),
    "unauthorized": (401, "A valid bearer credential is required."),
    "forbidden": (403, "The credential does not grant this operation."),
    "csrf_rejected": (403, "The browser request could not be verified."),
    "not_found": (404, "The requested resource was not found."),
    "conflict": (409, "The operation conflicts with current state."),
    "body_too_large": (413, "The request body exceeds the configured limit."),
    "url_not_allowed": (422, "The target URL is not allowed."),
    "resource_limit": (422, "The operation exceeds a configured safety limit."),
    "rate_limited": (429, "Too many requests. Try again later."),
    "unavailable": (503, "A required service capability is unavailable."),
    "internal_error": (500, "An internal error occurred."),
}


def public_error(code: str, *, field: str | None = None) -> PublicError:
    status, message = ERROR_CATALOG[code]
    return PublicError(code=code, message=message, status=status, field=field)


def correlation_id(candidate: str | None = None) -> str:
    if candidate and CORRELATION_RE.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


def public_error_payload(error: PublicError, request_id: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": {
            "code": error.code,
            "message": error.message,
            "correlation_id": request_id,
        }
    }
    if error.field:
        payload["error"]["field"] = error.field
    return payload
