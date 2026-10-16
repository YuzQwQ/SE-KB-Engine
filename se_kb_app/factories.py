from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from se_kb_app.errors import configuration_error
from se_kb_app.settings import AppSettings


ResourceFactory = Callable[[], object]


@dataclass(frozen=True)
class ClientFactories:
    """Lazy constructors for infrastructure owned by an application instance."""

    openai: ResourceFactory
    http: ResourceFactory
    vector_store: ResourceFactory
    browser: ResourceFactory
    tor: ResourceFactory

    def as_mapping(self) -> Mapping[str, ResourceFactory]:
        return {
            "openai": self.openai,
            "http": self.http,
            "vector_store": self.vector_store,
            "browser": self.browser,
            "tor": self.tor,
        }

    @classmethod
    def defaults(cls, settings: AppSettings) -> "ClientFactories":
        return cls(
            openai=lambda: _create_openai(settings),
            http=lambda: _create_http(settings),
            vector_store=lambda: _create_vector_store(settings),
            browser=_create_browser,
            tor=lambda: _create_tor(settings),
        )


class BrowserRenderer:
    def render(self, url: str, *, timeout_ms: int = 30_000) -> str | None:
        from utils.playwright_fetcher import fetch_rendered_html_sync

        return fetch_rendered_html_sync(url, timeout_ms=timeout_ms)

    def close(self) -> None:
        return None


def _create_openai(settings: AppSettings) -> object:
    if not settings.model_api_key:
        raise configuration_error("model_api_key", "Set OPENAI_API_KEY before using the model client.")
    from openai import OpenAI

    options: dict[str, Any] = {"api_key": settings.model_api_key,
                               "timeout": settings.model_timeout_seconds, "max_retries": 0}
    if settings.model_base_url:
        options["base_url"] = settings.model_base_url
    return OpenAI(**options)


def _create_http(settings: AppSettings) -> object:
    import httpx

    return httpx.Client(timeout=settings.http_timeout_seconds, follow_redirects=False)


def _create_vector_store(settings: AppSettings) -> Any:
    from vectorizer import KnowledgeRetriever, VectorConfig

    config = VectorConfig(
        kb_root=settings.paths.project / "se_kb",
        vector_store_path=settings.paths.project / "se_kb" / "vector_store",
        embedding_cache_path=settings.paths.data / "embedding_cache",
    )
    return KnowledgeRetriever(config)


def _create_browser() -> BrowserRenderer:
    return BrowserRenderer()


def _create_tor(settings: AppSettings) -> object:
    from se_kb_app.services.tor import TorController

    return TorController(enabled=settings.use_tor)
