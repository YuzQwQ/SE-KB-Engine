from __future__ import annotations

import hmac
import inspect
import os
from dataclasses import dataclass
from enum import IntEnum
from functools import wraps
from typing import Callable, Iterable, ParamSpec, TypeVar

from service_boundary.audit import audit_event
from service_boundary.errors import PublicError, public_error

P = ParamSpec("P")
R = TypeVar("R")


class Role(IntEnum):
    READ = 1
    ADMIN = 2


@dataclass(frozen=True)
class CredentialSet:
    read: tuple[str, ...]
    admin: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "CredentialSet":
        def values(name: str) -> tuple[str, ...]:
            return tuple(item.strip() for item in os.getenv(name, "").split(",") if item.strip())

        return cls(read=values("KB_READ_KEYS"), admin=values("KB_ADMIN_KEYS"))


def parse_bearer(headers: Iterable[str]) -> str:
    values = [value.strip() for value in headers if value and value.strip()]
    if not values:
        raise public_error("unauthorized")
    if len(values) != 1 or "," in values[0]:
        raise public_error("unauthorized")
    parts = values[0].split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise public_error("unauthorized")
    return parts[1]


def _matches(token: str, candidates: tuple[str, ...]) -> bool:
    matched = False
    for candidate in candidates:
        matched = hmac.compare_digest(token.encode(), candidate.encode()) or matched
    return matched


def authenticate(headers: Iterable[str], required: Role) -> Role:
    token = parse_bearer(headers)
    credentials = CredentialSet.from_environment()
    is_admin = _matches(token, credentials.admin)
    is_read = _matches(token, credentials.read)
    actual = Role.ADMIN if is_admin else Role.READ if is_read else None
    if actual is None:
        raise public_error("unauthorized")
    if actual < required:
        raise public_error("forbidden")
    return actual


def authorize_token(authorization: str | None, required: Role, request_id: str) -> Role:
    try:
        role = authenticate([authorization] if authorization else [], required)
    except PublicError:
        audit_event("authentication", "denied", request_id, required=required.name.lower())
        raise
    audit_event(
        "authentication",
        "granted",
        request_id,
        required=required.name.lower(),
        role=role.name.lower(),
    )
    return role


def protected(required: Role) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Protect non-Flask adapters that accept `authorization` and `correlation_id`."""

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def async_wrapped(*args: P.args, **kwargs: P.kwargs):
                request_id = str(kwargs.pop("correlation_id", "") or "local-mcp-request")
                authorization = kwargs.pop("authorization", None)
                authorize_token(str(authorization) if authorization else None, required, request_id)
                try:
                    result = await function(*args, **kwargs)
                except Exception:
                    audit_event(
                        "administrative_operation", "failed", request_id, operation=function.__name__
                    )
                    raise
                audit_event(
                    "administrative_operation", "succeeded", request_id, operation=function.__name__
                )
                return result

            return async_wrapped  # type: ignore[return-value]

        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            request_id = str(kwargs.pop("correlation_id", "") or "local-mcp-request")
            authorization = kwargs.pop("authorization", None)
            authorize_token(str(authorization) if authorization else None, required, request_id)
            try:
                result = function(*args, **kwargs)
            except Exception:
                audit_event(
                    "administrative_operation", "failed", request_id, operation=function.__name__
                )
                raise
            audit_event(
                "administrative_operation", "succeeded", request_id, operation=function.__name__
            )
            return result

        return wrapped

    return decorator
