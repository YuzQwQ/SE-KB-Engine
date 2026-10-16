from __future__ import annotations

import pytest

from se_kb_app.crawling.models import AttemptMode, FetchPolicy, FetchState, OutcomeKind
from se_kb_app.crawling.machine import FetchStateMachine
from se_kb_app.domain import FetchRequest, FetchedDocument
from se_kb_app.errors import ErrorKind, wrap_error
from se_kb_app.jobs.store import CancellationToken


class SequenceFetcher:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def fetch(self, request):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def close(self):
        return None


def document(content: str = "enough useful content for the fixture") -> FetchedDocument:
    return FetchedDocument("https://example.com/final", "title", content)


@pytest.mark.unit
def test_static_success_avoids_retry_and_browser_fallback():
    static = SequenceFetcher(document())
    rendered = SequenceFetcher(document("rendered content that should never run"))
    outcome = FetchStateMachine(static, rendered=rendered).run(FetchRequest("https://example.com"))
    assert outcome.kind is OutcomeKind.SUCCESS
    assert static.calls == 1
    assert rendered.calls == 0
    assert [attempt.mode for attempt in outcome.attempts] == [AttemptMode.STATIC]
    assert outcome.transitions[-1].target is FetchState.SUCCEEDED


@pytest.mark.unit
def test_typed_transient_failure_retries_within_budget():
    transient = wrap_error(
        ErrorKind.NETWORK,
        "upstream_busy",
        "The upstream is temporarily busy.",
        retryable=True,
        cause=TimeoutError(),
    )
    static = SequenceFetcher(transient, document())
    delays: list[float] = []
    outcome = FetchStateMachine(
        static,
        policy=FetchPolicy(maximum_static_attempts=2),
        sleep=delays.append,
    ).run(
        FetchRequest("https://example.com")
    )
    assert outcome.kind is OutcomeKind.SUCCESS
    assert static.calls == 2
    assert any(transition.target is FetchState.BACKOFF for transition in outcome.transitions)
    assert len(delays) == 1


@pytest.mark.unit
def test_policy_failure_never_uses_unrelated_fallback():
    blocked = wrap_error(
        ErrorKind.POLICY,
        "blocked_url",
        "URL is blocked by policy.",
        retryable=False,
        cause=ValueError(),
    )
    static = SequenceFetcher(blocked)
    rendered = SequenceFetcher(document())
    outcome = FetchStateMachine(static, rendered=rendered).run(FetchRequest("https://example.com"))
    assert outcome.kind is OutcomeKind.POLICY_FAILURE
    assert rendered.calls == 0


@pytest.mark.unit
def test_no_content_uses_one_rendered_fallback_and_classifies_challenge():
    static = SequenceFetcher(document("tiny"))
    rendered = SequenceFetcher(document("captcha challenge page with enough content"))
    outcome = FetchStateMachine(static, rendered=rendered).run(FetchRequest("https://example.com"))
    assert outcome.kind is OutcomeKind.CHALLENGE
    assert [attempt.mode for attempt in outcome.attempts] == [AttemptMode.STATIC, AttemptMode.RENDERED]


@pytest.mark.unit
def test_cancelled_fetch_never_contacts_static_or_browser():
    static = SequenceFetcher(document())
    rendered = SequenceFetcher(document())
    token = CancellationToken()
    token.cancel()
    outcome = FetchStateMachine(static, rendered=rendered).run(
        FetchRequest("https://example.com"), cancellation=token
    )
    assert outcome.kind is OutcomeKind.CANCELLED
    assert static.calls == 0 and rendered.calls == 0
