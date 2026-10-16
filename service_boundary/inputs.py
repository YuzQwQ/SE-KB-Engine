from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, TypeVar

from service_boundary.errors import public_error

T = TypeVar("T")
PATH_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class InputLimits:
    request_bytes: int = 1_048_576
    query_chars: int = 4_000
    content_chars: int = 2_000_000
    url_chars: int = 2_048
    json_chars: int = 1_000_000
    top_k_max: int = 100
    task_limit_max: int = 50
    list_items_max: int = 100

    @classmethod
    def from_environment(cls) -> "InputLimits":
        defaults = cls()

        def number(name: str, default: int) -> int:
            try:
                return max(1, int(os.getenv(name, str(default))))
            except ValueError:
                return default

        return cls(
            request_bytes=number("MAX_REQUEST_BYTES", defaults.request_bytes),
            query_chars=number("MAX_QUERY_CHARS", defaults.query_chars),
            content_chars=number("MAX_CONTENT_CHARS", defaults.content_chars),
            url_chars=number("MAX_URL_CHARS", defaults.url_chars),
            json_chars=number("MAX_JSON_CHARS", defaults.json_chars),
            top_k_max=number("MAX_TOP_K", defaults.top_k_max),
            task_limit_max=number("MAX_TASK_LIMIT", defaults.task_limit_max),
            list_items_max=number("MAX_LIST_ITEMS", defaults.list_items_max),
        )


def object_body(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise public_error("invalid_request")
    return value


def string_field(
    data: Mapping[str, Any], name: str, *, required: bool = False, max_length: int
) -> str | None:
    value = data.get(name)
    if value is None:
        if required:
            raise public_error("invalid_field", field=name)
        return None
    if not isinstance(value, str):
        raise public_error("invalid_field", field=name)
    value = value.strip()
    if (required and not value) or len(value) > max_length:
        raise public_error("invalid_field", field=name)
    return value


def integer_field(
    data: Mapping[str, Any], name: str, *, default: int, minimum: int, maximum: int
) -> int:
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise public_error("invalid_field", field=name)
    return value


def boolean_field(data: Mapping[str, Any], name: str, *, default: bool) -> bool:
    value = data.get(name, default)
    if not isinstance(value, bool):
        raise public_error("invalid_field", field=name)
    return value


def enum_field(data: Mapping[str, Any], name: str, allowed: Iterable[T]) -> T | None:
    value = data.get(name)
    if value in (None, ""):
        return None
    choices = tuple(allowed)
    if value not in choices:
        raise public_error("invalid_field", field=name)
    return value


def string_list_field(data: Mapping[str, Any], name: str, *, maximum: int) -> list[str]:
    value = data.get(name, [])
    if not isinstance(value, list) or len(value) > maximum:
        raise public_error("invalid_field", field=name)
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise public_error("invalid_field", field=name)
    return [item.strip() for item in value]


def date_field(value: object, name: str = "date") -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise public_error("invalid_field", field=name)
    try:
        datetime.strptime(value, "%Y/%m/%d")
    except ValueError as exc:
        raise public_error("invalid_field", field=name) from exc
    return value


def path_component(value: object, name: str) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or not PATH_COMPONENT.fullmatch(value) or value in {".", ".."}:
        raise public_error("invalid_field", field=name)
    return value


def confined_path(root: str | Path, candidate: object, name: str = "path") -> Path:
    root_path = Path(root).resolve()
    if candidate in (None, "", str(root)):
        target = root_path
    elif not isinstance(candidate, str):
        raise public_error("invalid_field", field=name)
    else:
        supplied = Path(candidate)
        target = supplied.resolve() if supplied.is_absolute() else (root_path / supplied).resolve()
    try:
        target.relative_to(root_path)
    except ValueError as exc:
        raise public_error("invalid_field", field=name) from exc
    return target
