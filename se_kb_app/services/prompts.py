from __future__ import annotations

import json
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from se_kb_app.errors import ErrorKind, wrap_error
from se_kb_app.settings import SearchEngine


class PromptRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def load(self, name: str) -> str | Mapping[str, Any]:
        if not name or Path(name).name != name:
            raise ValueError("prompt name must be one file name")
        path = (self.root / name).resolve()
        if path.parent != self.root:
            raise ValueError("prompt path escapes the configured root")
        try:
            content = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".json":
                value = json.loads(content)
                if not isinstance(value, dict):
                    raise ValueError("prompt JSON must be an object")
                return MappingProxyType(value)
            if path.suffix.lower() == ".toml":
                return MappingProxyType(tomllib.loads(content))
            return content
        except (OSError, UnicodeError, ValueError, tomllib.TOMLDecodeError) as error:
            raise wrap_error(
                ErrorKind.CONFIGURATION,
                "prompt_load_failed",
                f"Prompt '{name}' could not be loaded.",
                retryable=False,
                cause=error,
                metadata={"prompt": name},
            ) from error


SearchHandler = Callable[[str, int], object]


class SearchEngineRegistry:
    _ALIASES = {"ddg": SearchEngine.DUCKDUCKGO, "duck": SearchEngine.DUCKDUCKGO}

    def __init__(self) -> None:
        self._handlers: dict[SearchEngine, SearchHandler] = {}

    def register(self, engine: SearchEngine | str, handler: SearchHandler) -> None:
        self._handlers[self.parse(engine)] = handler

    def parse(self, value: SearchEngine | str) -> SearchEngine:
        if isinstance(value, SearchEngine):
            return value
        normalized = value.strip().lower()
        if normalized in self._ALIASES:
            return self._ALIASES[normalized]
        return SearchEngine(normalized)

    def search(self, engine: SearchEngine | str, query: str, limit: int) -> object:
        selected = self.parse(engine)
        try:
            handler = self._handlers[selected]
        except KeyError as error:
            raise wrap_error(
                ErrorKind.CONFIGURATION,
                "search_engine_unavailable",
                f"Search engine '{selected.value}' is not configured.",
                retryable=False,
                cause=error,
                metadata={"engine": selected.value},
            ) from error
        return handler(query, limit)
