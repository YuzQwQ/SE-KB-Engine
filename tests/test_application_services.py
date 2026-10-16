from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from se_kb_app.domain import (
    ExtractionRequest,
    ExtractionResult,
    FetchRequest,
    FetchedDocument,
    RetrievalRequest,
    RetrievalResult,
    StoredArtifact,
)
from se_kb_app.errors import ApplicationError, ErrorKind, wrap_error
from se_kb_app.services.crawl import CrawlOrchestrator
from se_kb_app.services.events import InMemoryEventPublisher
from se_kb_app.services.knowledge import KnowledgeOrchestrator
from se_kb_app.services.prompts import PromptRepository, SearchEngineRegistry
from se_kb_app.services.retrieval import DfdContextService, RetrievalService
from se_kb_app.services.tor import TorController


class FakeFetcher:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def fetch(self, request):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def close(self):
        return None


@pytest.mark.unit
def test_crawl_retries_typed_network_errors_then_stops_on_policy_failure():
    retryable = wrap_error(
        ErrorKind.NETWORK,
        "temporary_network_failure",
        "Temporary network failure.",
        retryable=True,
        cause=TimeoutError(),
    )
    non_retryable = wrap_error(
        ErrorKind.POLICY,
        "blocked_url",
        "URL is blocked.",
        retryable=False,
        cause=ValueError(),
    )
    rendered_document = FetchedDocument("https://example.com", "Rendered", "body")
    attempts: list[tuple[str, int]] = []
    service = CrawlOrchestrator(
        FakeFetcher([retryable, non_retryable]),
        rendered=FakeFetcher([rendered_document]),
        max_retries=4,
        on_attempt=lambda mode, attempt: attempts.append((mode, attempt)),
    )

    with pytest.raises(ApplicationError) as blocked:
        service.fetch(FetchRequest("https://example.com"))
    assert blocked.value.public_code == "blocked_url"
    assert attempts == [("direct", 1), ("direct", 2)]


@pytest.mark.unit
def test_prompt_repository_and_search_registry(tmp_path: Path):
    (tmp_path / "prompt.toml").write_text('system = "safe"\n', encoding="utf-8")
    assert PromptRepository(tmp_path).load("prompt.toml") == {"system": "safe"}
    registry = SearchEngineRegistry()
    registry.register("duckduckgo", lambda query, limit: [query, limit])
    assert registry.search("ddg", "typed errors", 2) == ["typed errors", 2]
    with pytest.raises(ValueError):
        PromptRepository(tmp_path).load("../secret")


class FakeExtractor:
    def extract(self, request):
        return ExtractionResult(({"content": request.content},))


class FakeStore:
    def save(self, result):
        return [StoredArtifact("one", Path("one.json"))]

    def close(self):
        return None


@pytest.mark.unit
def test_knowledge_orchestration_runs_visual_extract_validate_and_save():
    calls: list[str] = []

    def visual(request: ExtractionRequest) -> ExtractionRequest:
        calls.append("visual")
        return ExtractionRequest(request.content + "+image")

    def validate(result: ExtractionResult) -> None:
        calls.append("validate")
        assert result.artifacts[0]["content"] == "text+image"

    service = KnowledgeOrchestrator(FakeExtractor(), FakeStore(), validator=validate, visual_analyzer=visual)
    result, stored = service.extract_and_save(ExtractionRequest("text"))
    assert result.artifacts[0]["content"] == "text+image"
    assert stored[0].identifier == "one"
    assert calls == ["visual", "validate"]


class FakeRetriever:
    def retrieve(self, request):
        return RetrievalResult(request.query, request.intent or "auto", ({"content": "answer"},))

    def close(self):
        return None


@pytest.mark.unit
def test_retrieval_publishes_realtime_safe_event():
    events = InMemoryEventPublisher()
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    service = RetrievalService(FakeRetriever(), events=events, clock=lambda: now)
    result = service.retrieve(RetrievalRequest("question", 3))
    assert result.items == ({"content": "answer"},)
    assert events.snapshot()[0].payload == {"query": "question", "items": 1}


@pytest.mark.unit
def test_dfd_context_uses_shared_retrieval_for_stable_sections():
    context = DfdContextService(RetrievalService(FakeRetriever())).build("checkout")
    assert tuple(context) == ("concepts", "rules", "examples")
    assert context["rules"].intent == "rule"


class FakeProcess:
    def __init__(self) -> None:
        self.terminated = False

    def poll(self):
        return None if not self.terminated else 0

    def terminate(self):
        self.terminated = True

    def wait(self, timeout):
        return 0

    def kill(self):
        self.terminated = True


@pytest.mark.unit
def test_tor_construction_has_no_process_side_effect_and_lifecycle_is_explicit(tmp_path: Path):
    calls = []

    def create_process(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess()

    controller = TorController(enabled=True, data_dir=tmp_path, process_factory=create_process)
    assert calls == []
    assert controller.start() is True
    assert len(calls) == 1
    assert controller.proxy_url == "socks5://127.0.0.1:9050"
    controller.close()
    assert controller.running is False
