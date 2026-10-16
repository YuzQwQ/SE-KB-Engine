from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from se_kb_app.errors import ApplicationError, ErrorKind, wrap_error
from se_kb_app.factories import ClientFactories, ResourceFactory
from se_kb_app.settings import AppSettings
from se_kb_app.observability import METRICS, configure_logging


Clock = Callable[[], datetime]


@dataclass(frozen=True)
class CapabilityReadiness:
    available: bool
    public_code: str | None = None


class Application:
    """Composition root and lifecycle owner for one runtime process."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        factories: Mapping[str, ResourceFactory] | None = None,
        services: Mapping[str, object] | None = None,
        clock: Clock | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.logger = logger or logging.getLogger("se_kb_app")
        self._factories = dict(factories or {})
        self._resources = dict(services or {})
        self._owned: list[str] = []
        self._readiness: dict[str, CapabilityReadiness] = {
            name: CapabilityReadiness(True) for name in self._resources
        }

    @property
    def readiness(self) -> Mapping[str, CapabilityReadiness]:
        return MappingProxyType(dict(self._readiness))

    def start(self, capabilities: Iterable[str] | None = None) -> Mapping[str, CapabilityReadiness]:
        names = list(capabilities if capabilities is not None else self._factories)
        created: list[str] = []
        for name in names:
            try:
                already_created = name in self._resources
                self.resource(name)
                if not already_created and name in self._owned:
                    created.append(name)
            except ApplicationError as error:
                self._rollback(created, failed=name, error=error)
                break
            except Exception as error:
                wrapped = wrap_error(
                    ErrorKind.INTERNAL,
                    "capability_start_failed",
                    f"Capability '{name}' is unavailable.",
                    retryable=False,
                    cause=error,
                    metadata={"capability": name},
                )
                self._rollback(created, failed=name, error=wrapped)
                break
        return self.readiness

    def resource(self, name: str) -> object:
        if name in self._resources:
            return self._resources[name]
        factory = self._factories.get(name)
        if factory is None:
            raise KeyError(name)
        resource = factory()
        self._resources[name] = resource
        self._owned.append(name)
        self._readiness[name] = CapabilityReadiness(True)
        return resource

    def close(self) -> None:
        self._close_names(reversed(self._owned))
        self._owned.clear()

    def _rollback(self, created: list[str], *, failed: str, error: ApplicationError) -> None:
        self._close_names(reversed(created))
        for name in created:
            self._readiness[name] = CapabilityReadiness(False, "startup_rolled_back")
        self._readiness[failed] = CapabilityReadiness(False, error.public_code)
        self.logger.error("Capability startup failed", extra={"capability": failed})

    def _close_names(self, names: Iterable[str]) -> None:
        for name in list(names):
            resource = self._resources.pop(name, None)
            if resource is None:
                continue
            closer = getattr(resource, "close", None) or getattr(resource, "shutdown", None)
            if callable(closer):
                try:
                    closer()
                    METRICS.increment("resource_cleanup_total", capability=name, outcome="succeeded")
                except Exception as error:
                    METRICS.increment("resource_cleanup_total", capability=name, outcome="failed")
                    self.logger.warning(
                        "Resource cleanup failed",
                        extra={"capability": name, "error_type": type(error).__name__},
                    )
            if name in self._owned:
                self._owned.remove(name)


class ApplicationBuilder:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.factories: dict[str, ResourceFactory] = {}
        self.services: dict[str, object] = {}
        self.clock: Clock | None = None
        self.logger: logging.Logger | None = None

    def with_default_clients(self) -> "ApplicationBuilder":
        self.factories.update(ClientFactories.defaults(self.settings).as_mapping())
        return self

    def with_default_services(self) -> "ApplicationBuilder":
        from se_kb_app.crawling.runtime import create_crawl_service
        from se_kb_app.infrastructure.vector import create_vector_retrieval
        from se_kb_app.services.events import InMemoryEventPublisher
        from se_kb_app.services.prompts import PromptRepository, SearchEngineRegistry

        self.factories.update(
            {
                "crawl": lambda: create_crawl_service(self.settings),
                "retrieval": lambda: create_vector_retrieval(self.settings),
                "events": InMemoryEventPublisher,
                "prompts": lambda: PromptRepository(self.settings.paths.config),
                "search_registry": SearchEngineRegistry,
            }
        )
        if self.settings.obsidian.enabled:
            from se_kb_app.obsidian.service import create_obsidian_service

            self.factories["obsidian"] = lambda: create_obsidian_service(self.settings)
        return self

    def with_factory(self, name: str, factory: ResourceFactory) -> "ApplicationBuilder":
        self.factories[name] = factory
        return self

    def with_service(self, name: str, service: object) -> "ApplicationBuilder":
        self.services[name] = service
        return self

    def build(self) -> Application:
        return Application(
            self.settings,
            factories=self.factories,
            services=self.services,
            clock=self.clock,
            logger=self.logger,
        )


def create_application(
    settings: AppSettings | None = None,
    *,
    include_default_clients: bool = False,
    include_default_services: bool = False,
) -> Application:
    configure_logging()
    resolved = settings or AppSettings.from_sources()
    builder = ApplicationBuilder(resolved)
    if include_default_clients:
        builder.with_default_clients()
    if include_default_services:
        builder.with_default_services()
    return builder.build()
