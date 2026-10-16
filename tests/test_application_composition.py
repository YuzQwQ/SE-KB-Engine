from __future__ import annotations

from pathlib import Path

import pytest

from se_kb_app.composition import Application, ApplicationBuilder, create_application
from se_kb_app.settings import AppSettings


class FakeResource:
    def __init__(self, name: str, events: list[str]) -> None:
        self.name = name
        self.events = events

    def close(self) -> None:
        self.events.append(f"close:{self.name}")


def settings_for(tmp_path: Path) -> AppSettings:
    return AppSettings.from_sources(environ={}, overrides={"project_root": tmp_path})


@pytest.mark.unit
def test_resources_are_lazy_and_replaceable(tmp_path: Path):
    events: list[str] = []
    injected = object()

    def create_http() -> FakeResource:
        events.append("create:http")
        return FakeResource("http", events)

    application = ApplicationBuilder(settings_for(tmp_path)).with_service("search", injected).with_factory(
        "http", create_http
    ).build()

    assert events == []
    assert application.resource("search") is injected
    first = application.resource("http")
    assert application.resource("http") is first
    assert events == ["create:http"]
    application.close()
    assert events == ["create:http", "close:http"]


@pytest.mark.unit
def test_partial_startup_rolls_back_in_reverse_order_and_reports_readiness(tmp_path: Path):
    events: list[str] = []

    def create(name: str):
        def factory() -> FakeResource:
            events.append(f"create:{name}")
            return FakeResource(name, events)

        return factory

    def fail():
        events.append("create:broken")
        raise RuntimeError("private startup detail")

    application = Application(
        settings_for(tmp_path),
        factories={"first": create("first"), "second": create("second"), "broken": fail},
    )
    readiness = application.start()

    assert events == [
        "create:first",
        "create:second",
        "create:broken",
        "close:second",
        "close:first",
    ]
    assert readiness["first"].available is False
    assert readiness["second"].public_code == "startup_rolled_back"
    assert readiness["broken"].public_code == "capability_start_failed"


@pytest.mark.unit
def test_compatibility_factory_is_offline_until_a_resource_is_requested(tmp_path: Path):
    application = create_application(settings_for(tmp_path), include_default_clients=True)
    assert set(application.readiness) == set()
    application.close()
