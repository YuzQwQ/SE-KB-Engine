from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from se_kb_app.errors import ApplicationError, configuration_error
from se_kb_app.paths import ProjectPaths
from service_boundary.errors import PublicError
from service_boundary.url_policy import parse_http_url


class SearchEngine(str, Enum):
    GOOGLE = "google"
    BING = "bing"
    BAIDU = "baidu"
    DUCKDUCKGO = "duckduckgo"


ENV_FIELDS = {
    "SE_KB_PROJECT_ROOT": "project_root",
    "CONFIG_ROOT": "config_root",
    "DATA_ROOT": "data_root",
    "CACHE_ROOT": "cache_root",
    "OUTPUT_ROOT": "output_root",
    "BASE_URL": "model_base_url",
    "MODEL": "model",
    "OPENAI_API_KEY": "model_api_key",
    "DEFAULT_SEARCH_ENGINE": "search_engine",
    "HTTP_TIMEOUT_SECONDS": "http_timeout_seconds",
    "HTTP_MAX_RETRIES": "http_max_retries",
    "USE_TOR": "use_tor",
    "CRAWL_WORKERS": "crawl_workers",
    "CRAWL_PER_HOST": "crawl_per_host",
    "CRAWL_WAITING": "crawl_waiting",
    "CRAWL_MIN_INTERVAL": "crawl_min_interval",
    "PROXY_URL": "crawl_proxy_url",
    "MODEL_TIMEOUT_SECONDS": "model_timeout_seconds",
    "OBSIDIAN_VAULT_ROOT": "obsidian_vault_root",
    "OBSIDIAN_VAULT_NAME": "obsidian_vault_name",
    "OBSIDIAN_MANAGED_DIRECTORY": "obsidian_managed_directory",
    "OBSIDIAN_ENTITY_KINDS": "obsidian_entity_kinds",
    "OBSIDIAN_SEMANTIC_EDGES": "obsidian_semantic_edges",
    "OBSIDIAN_SEMANTIC_MIN_SCORE": "obsidian_semantic_min_score",
    "OBSIDIAN_SEMANTIC_MAX_NEIGHBORS": "obsidian_semantic_max_neighbors",
    "OBSIDIAN_GRAPH_NODE_LIMIT": "obsidian_graph_node_limit",
    "OBSIDIAN_CANVAS_ENABLED": "obsidian_canvas_enabled",
}


@dataclass(frozen=True)
class ObsidianSettings:
    vault_root: Path | None = None
    vault_name: str | None = None
    managed_directory: str = "SE-KB"
    entity_kinds: tuple[str, ...] = ("concept", "rule", "pattern", "example")
    semantic_edges: bool = True
    semantic_min_score: float = 0.75
    semantic_max_neighbors: int = 5
    graph_node_limit: int = 500
    canvas_enabled: bool = False

    @property
    def enabled(self) -> bool:
        return self.vault_root is not None


@dataclass(frozen=True)
class CrawlSettings:
    workers: int = 4
    per_host: int = 1
    waiting: int = 16
    min_interval: float = 1.0
    proxy_url: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class AppSettings:
    paths: ProjectPaths
    model_base_url: str | None = None
    model: str | None = None
    model_api_key: str | None = field(default=None, repr=False)
    search_engine: SearchEngine = SearchEngine.GOOGLE
    http_timeout_seconds: float = 20.0
    http_max_retries: int = 3
    use_tor: bool = False
    obsidian: ObsidianSettings = field(default_factory=ObsidianSettings)
    crawl: CrawlSettings = field(default_factory=CrawlSettings)
    model_timeout_seconds: float = 60.0

    @classmethod
    def from_sources(
        cls,
        *,
        config_file: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
        overrides: Mapping[str, Any] | None = None,
    ) -> "AppSettings":
        env = os.environ if environ is None else environ
        explicit = dict(overrides or {})
        project_hint = explicit.get("project_root") or env.get("SE_KB_PROJECT_ROOT")
        initial_paths = ProjectPaths.resolve(project_hint)
        selected_config = Path(config_file).resolve() if config_file else initial_paths.config / "application.toml"
        values: dict[str, Any] = {}
        if selected_config.is_file():
            try:
                if selected_config.suffix.lower() == ".json":
                    loaded = json.loads(selected_config.read_text(encoding="utf-8"))
                else:
                    loaded = tomllib.loads(selected_config.read_text(encoding="utf-8"))
                if not isinstance(loaded, dict):
                    raise ValueError("configuration root must be an object")
                obsidian = loaded.pop("obsidian", None)
                if obsidian is not None:
                    if not isinstance(obsidian, dict):
                        raise ValueError("obsidian configuration must be an object")
                    values.update({f"obsidian_{key}": value for key, value in obsidian.items()})
                crawl = loaded.pop("crawl", None)
                if crawl is not None:
                    if not isinstance(crawl, dict):
                        raise ValueError("crawl configuration must be an object")
                    values.update({f"crawl_{key}": value for key, value in crawl.items()})
                values.update(loaded)
            except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
                raise configuration_error(
                    "config_file", "Use a readable TOML or JSON object.", cause=error
                ) from error
        for environment_name, field_name in ENV_FIELDS.items():
            if environment_name in env:
                values[field_name] = env[environment_name]
        values.update(explicit)
        return cls._validated(values)

    @classmethod
    def _validated(cls, values: Mapping[str, Any]) -> "AppSettings":
        try:
            paths = ProjectPaths.resolve(
                values.get("project_root"),
                config_root=values.get("config_root"),
                data_root=values.get("data_root"),
                cache_root=values.get("cache_root"),
                output_root=values.get("output_root"),
            )
            base_url = _optional_string(values.get("model_base_url"), "model_base_url")
            if base_url:
                try:
                    parse_http_url(base_url)
                except PublicError as error:
                    raise configuration_error(
                        "model_base_url", "Use an HTTP or HTTPS URL.", cause=error
                    ) from error
            model = _optional_string(values.get("model"), "model")
            secret = _optional_string(values.get("model_api_key"), "model_api_key")
            engine = _search_engine(values.get("search_engine", SearchEngine.GOOGLE))
            timeout = _positive_float(values.get("http_timeout_seconds", 20.0), "http_timeout_seconds")
            retries = _bounded_int(values.get("http_max_retries", 3), "http_max_retries", 0, 10)
            use_tor = _boolean(values.get("use_tor", False), "use_tor")
            obsidian = _obsidian_settings(values)
            workers = _bounded_int(values.get("crawl_workers", 4), "crawl_workers", 1, 16)
            crawl = CrawlSettings(workers=workers,
                per_host=_bounded_int(values.get("crawl_per_host", 1), "crawl_per_host", 1, workers),
                waiting=_bounded_int(values.get("crawl_waiting", 16), "crawl_waiting", 0, 256),
                min_interval=_bounded_float(values.get("crawl_min_interval", 1), "crawl_min_interval", 0, 60),
                proxy_url=_optional_string(values.get("crawl_proxy_url"), "crawl_proxy_url"))
        except ApplicationError:
            raise
        except (TypeError, ValueError) as error:
            raise configuration_error("settings", "Review the documented value types.", cause=error) from error
        return cls(
            paths=paths,
            model_base_url=base_url,
            model=model,
            model_api_key=secret,
            search_engine=engine,
            http_timeout_seconds=timeout,
            http_max_retries=retries,
            use_tor=use_tor,
            model_timeout_seconds=_positive_float(values.get("model_timeout_seconds", 60), "model_timeout_seconds"),
            crawl=crawl,
            obsidian=obsidian,
        )


def _optional_string(value: Any, setting: str) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise configuration_error(setting, "Use a string value.")
    return value.strip()


def _positive_float(value: Any, setting: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise configuration_error(setting, "Use a positive number.", cause=error) from error
    if parsed <= 0 or parsed > 600:
        raise configuration_error(setting, "Use a number greater than 0 and at most 600.")
    return parsed


def _bounded_int(value: Any, setting: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise configuration_error(setting, f"Use an integer from {minimum} to {maximum}.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise configuration_error(setting, f"Use an integer from {minimum} to {maximum}.", cause=error) from error
    if not minimum <= parsed <= maximum:
        raise configuration_error(setting, f"Use an integer from {minimum} to {maximum}.")
    return parsed


def _boolean(value: Any, setting: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"1", "true", "yes"}:
        return True
    if isinstance(value, str) and value.lower() in {"0", "false", "no", ""}:
        return False
    raise configuration_error(setting, "Use true or false.")


def _bounded_float(value: Any, setting: str, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise configuration_error(setting, f"Use a number from {minimum} to {maximum}.", cause=error) from error
    if not minimum <= parsed <= maximum:
        raise configuration_error(setting, f"Use a number from {minimum} to {maximum}.")
    return parsed


def _string_tuple(value: Any, setting: str) -> tuple[str, ...]:
    if isinstance(value, str):
        items: list[Any] = value.split(",")
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise configuration_error(setting, "Use a comma-separated string or string array.")
    normalized: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise configuration_error(setting, "Use non-empty names.")
        candidate = item.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", candidate):
            raise configuration_error(setting, "Use lowercase names containing letters, digits, '_' or '-'.")
        if candidate not in normalized:
            normalized.append(candidate)
    if not normalized:
        raise configuration_error(setting, "Select at least one entity kind.")
    return tuple(normalized)


def _managed_directory(value: Any) -> str:
    setting = "obsidian_managed_directory"
    if not isinstance(value, str) or not value.strip():
        raise configuration_error(setting, "Use a non-empty relative directory.")
    candidate = value.strip().replace("\\", "/")
    path = Path(candidate)
    if (
        path.is_absolute()
        or candidate.startswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(ord(char) < 32 for char in candidate)
    ):
        raise configuration_error(setting, "Use a bounded relative directory without traversal.")
    return path.as_posix()


def _obsidian_settings(values: Mapping[str, Any]) -> ObsidianSettings:
    root_value = values.get("obsidian_vault_root")
    if root_value in (None, ""):
        root = None
    elif isinstance(root_value, (str, Path)):
        root = Path(root_value).expanduser().resolve()
    else:
        raise configuration_error("obsidian_vault_root", "Use a filesystem path string.")
    name = _optional_string(values.get("obsidian_vault_name"), "obsidian_vault_name")
    if name is not None and (any(ord(char) < 32 for char in name) or len(name) > 160):
        raise configuration_error("obsidian_vault_name", "Use a printable name of at most 160 characters.")
    return ObsidianSettings(
        vault_root=root,
        vault_name=name,
        managed_directory=_managed_directory(values.get("obsidian_managed_directory", "SE-KB")),
        entity_kinds=_string_tuple(
            values.get("obsidian_entity_kinds", ("concept", "rule", "pattern", "example")),
            "obsidian_entity_kinds",
        ),
        semantic_edges=_boolean(values.get("obsidian_semantic_edges", True), "obsidian_semantic_edges"),
        semantic_min_score=_bounded_float(
            values.get("obsidian_semantic_min_score", 0.75),
            "obsidian_semantic_min_score",
            0.0,
            1.0,
        ),
        semantic_max_neighbors=_bounded_int(
            values.get("obsidian_semantic_max_neighbors", 5),
            "obsidian_semantic_max_neighbors",
            0,
            100,
        ),
        graph_node_limit=_bounded_int(
            values.get("obsidian_graph_node_limit", 500),
            "obsidian_graph_node_limit",
            10,
            5000,
        ),
        canvas_enabled=_boolean(values.get("obsidian_canvas_enabled", False), "obsidian_canvas_enabled"),
    )


def _search_engine(value: Any) -> SearchEngine:
    try:
        return SearchEngine(value)
    except (TypeError, ValueError) as error:
        allowed = ", ".join(engine.value for engine in SearchEngine)
        raise configuration_error("search_engine", f"Use one of: {allowed}.", cause=error) from error
