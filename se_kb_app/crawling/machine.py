from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from time import monotonic
from time import sleep as default_sleep

from se_kb_app.crawling.models import (
    AttemptMode,
    ContentClassification,
    FetchAttempt,
    FetchOutcome,
    FetchPolicy,
    FetchState,
    FetchTransition,
    OutcomeKind,
)
from se_kb_app.crawling.backoff import BackoffPolicy
from se_kb_app.domain import Cancellation, FetchRequest, FetchedDocument, Fetcher
from se_kb_app.errors import ApplicationError, ErrorKind
from se_kb_app.observability import METRICS


Classifier = Callable[[FetchedDocument, FetchPolicy], ContentClassification]
Clock = Callable[[], float]


def classify_document(document: FetchedDocument, policy: FetchPolicy) -> ContentClassification:
    if not document.media_type.startswith(("text/", "application/xhtml")):
        return ContentClassification.UNSUPPORTED
    from bs4 import BeautifulSoup
    from utils.html_cleaner import clean_and_structure
    from service_boundary.html_policy import enforce_html_budget
    from service_boundary.errors import PublicError
    from se_kb_app.errors import wrap_error

    try:
        enforce_html_budget(document.content)
    except PublicError as error:
        raise wrap_error(ErrorKind.POLICY, error.code, "HTML structure exceeded its limit.",
                         retryable=False, cause=error) from error

    soup = BeautifulSoup(document.content, "html.parser")
    title = (document.title or (soup.title.get_text() if soup.title else "")).strip().lower()
    text = soup.get_text(" ", strip=True).lower()
    if (title in {"just a moment...", "just a moment", "login required", "access denied"}
            or soup.select_one('input[type="password"], .g-recaptcha, #cf-challenge-running, #challenge-form')
            or text.startswith("captcha challenge")):
        return ContentClassification.CHALLENGE
    parsed = clean_and_structure(document.content, document.url)
    if len(parsed["clean_text"].strip()) < policy.minimum_content_chars:
        return ContentClassification.NO_CONTENT
    return ContentClassification.ACCEPTABLE


class FetchStateMachine:
    def __init__(
        self,
        static: Fetcher,
        *,
        rendered: Fetcher | None = None,
        policy: FetchPolicy | None = None,
        classifier: Classifier = classify_document,
        clock: Clock = monotonic,
        backoff: BackoffPolicy | None = None,
        sleep: Callable[[float], None] = default_sleep,
    ) -> None:
        self.static = static
        self.rendered = rendered
        self.policy = policy or FetchPolicy()
        configure = getattr(static, "configure_policy", None)
        if callable(configure):
            configure(self.policy)
        self.classifier = classifier
        self.clock = clock
        self.backoff = backoff or BackoffPolicy()
        self.sleep = sleep

    def run(self, request: FetchRequest, cancellation: Cancellation | None = None) -> FetchOutcome:
        started = self.clock()
        cancellation = cancellation or request.cancellation
        end = min(request.deadline if request.deadline is not None else float("inf"),
                  started + self.policy.total_timeout_seconds)
        request = replace(request, deadline=end, cancellation=cancellation)
        attempts: list[FetchAttempt] = []
        transitions: list[FetchTransition] = []
        self._transition(transitions, FetchState.VALIDATING, FetchState.STATIC, "policy_at_transport_boundary")
        last_error: ApplicationError | None = None

        def checkpoint():
            if cancellation:
                cancellation.checkpoint()
            if self.clock() >= end:
                raise ApplicationError(ErrorKind.NETWORK, "crawl_deadline", "Crawl deadline exceeded.")

        def failure(error, state):
            kind = (OutcomeKind.CANCELLED if error.kind is ErrorKind.CANCELLATION else
                    OutcomeKind.POLICY_FAILURE if error.kind is ErrorKind.POLICY else
                    OutcomeKind.TRANSIENT_FAILURE if error.retryable else OutcomeKind.PERMANENT_FAILURE)
            self._transition(transitions, state, FetchState.CANCELLED if kind is OutcomeKind.CANCELLED
                             else FetchState.FAILED, error.public_code)
            return self._outcome(kind, request.url, started, attempts, transitions)

        insufficient = False
        maximum = min(self.policy.maximum_static_attempts, max(1, request.maximum_attempts))
        for number in range(1, maximum + 1):
            attempt_started = self.clock()
            try:
                checkpoint()
                document = self.static.fetch(request)
                checkpoint()
                classification = self.classifier(document, self.policy)
                checkpoint()
                attempts.append(FetchAttempt(number, AttemptMode.STATIC, attempt_started,
                                             self.clock() - attempt_started, FetchState.CLASSIFYING,
                                             classification.value))
                self._transition(transitions, FetchState.STATIC, FetchState.CLASSIFYING, "response_received")
                if classification is ContentClassification.ACCEPTABLE:
                    self._transition(transitions, FetchState.CLASSIFYING, FetchState.SUCCEEDED, "acceptable_content")
                    return self._outcome(OutcomeKind.SUCCESS, request.url, started, attempts, transitions, document)
                if classification is ContentClassification.CHALLENGE:
                    return self._classified_failure(OutcomeKind.CHALLENGE, request.url, started,
                                                    attempts, transitions, "challenge_detected")
                if classification is ContentClassification.UNSUPPORTED:
                    return self._classified_failure(OutcomeKind.PERMANENT_FAILURE, request.url, started,
                                                    attempts, transitions, "unsupported_media")
                insufficient = True
                break
            except ApplicationError as error:
                last_error = error
                attempts.append(FetchAttempt(number, AttemptMode.STATIC, attempt_started,
                                             self.clock() - attempt_started, FetchState.STATIC,
                                             "typed_error", error.public_code, error.retryable))
                if not error.retryable or error.kind in {ErrorKind.CANCELLATION, ErrorKind.POLICY, ErrorKind.CONFIGURATION}:
                    return failure(error, FetchState.STATIC)
                if number == maximum:
                    break
                retry_after = error.metadata.get("retry_after")
                delay = self.backoff.delay(number, retry_after=str(retry_after) if retry_after is not None else None)
                if delay >= end - self.clock():
                    return failure(error, FetchState.STATIC)
                self._transition(transitions, FetchState.STATIC, FetchState.BACKOFF, f"{error.public_code}:{delay:.3f}s")
                try:
                    if cancellation is None:
                        self.sleep(delay)
                    else:
                        remaining = delay
                        while remaining > 0:
                            checkpoint()
                            interval = min(remaining, 0.05)
                            self.sleep(interval)
                            remaining -= interval
                    checkpoint()
                except ApplicationError as stopped:
                    return failure(stopped, FetchState.BACKOFF)
                self._transition(transitions, FetchState.BACKOFF, FetchState.STATIC, "retry_budget_available")
        # Network exhaustion is not evidence of a JavaScript page.
        if not insufficient:
            return failure(last_error or ApplicationError(ErrorKind.NETWORK, "fetch_failed", "Fetch failed."), FetchState.STATIC)
        if self.policy.allow_rendered_fallback and self.rendered is not None:
            self._transition(transitions, transitions[-1].target, FetchState.RENDERED, "static_content_insufficient")
            attempt_started = self.clock()
            try:
                checkpoint()
                document = self.rendered.fetch(request)
                checkpoint()
                classification = self.classifier(document, self.policy)
                checkpoint()
                attempts.append(FetchAttempt(len(attempts) + 1, AttemptMode.RENDERED, attempt_started,
                                             self.clock() - attempt_started, FetchState.CLASSIFYING, classification.value))
                if classification is ContentClassification.ACCEPTABLE:
                    self._transition(transitions, FetchState.RENDERED, FetchState.SUCCEEDED, "rendered_content_accepted")
                    return self._outcome(OutcomeKind.SUCCESS, request.url, started, attempts, transitions, document)
                kind = OutcomeKind.CHALLENGE if classification is ContentClassification.CHALLENGE else OutcomeKind.NO_CONTENT
                return self._classified_failure(kind, request.url, started, attempts, transitions, classification.value)
            except ApplicationError as error:
                attempts.append(FetchAttempt(len(attempts) + 1, AttemptMode.RENDERED, attempt_started,
                                             self.clock() - attempt_started, FetchState.RENDERED,
                                             "typed_error", error.public_code, error.retryable))
                return failure(error, FetchState.RENDERED)
        return self._classified_failure(OutcomeKind.NO_CONTENT, request.url, started, attempts, transitions,
                                        "no_acceptable_content")

    def _classified_failure(self, kind, url, started, attempts, transitions, reason):
        self._transition(transitions, transitions[-1].target, FetchState.FAILED, reason)
        return self._outcome(kind, url, started, attempts, transitions)

    def _outcome(self, kind, url, started, attempts, transitions, document=None):
        elapsed = self.clock() - started
        METRICS.increment("crawl_outcomes_total", outcome=kind.value)
        METRICS.increment("crawl_attempts_total", value=len(attempts), outcome=kind.value)
        METRICS.increment("crawl_retries_total", value=max(0, sum(a.mode is AttemptMode.STATIC for a in attempts) - 1), outcome=kind.value)
        METRICS.observe("stage_duration_ms", elapsed * 1000, stage="crawl", outcome=kind.value)
        return FetchOutcome(
            kind=kind,
            final_url=document.url if document else url,
            elapsed_seconds=elapsed,
            attempts=tuple(attempts),
            transitions=tuple(transitions),
            document=document,
            media_type=document.media_type if document else None,
            status_code=document.status_code if document else None,
        )

    @staticmethod
    def _transition(transitions, source, target, reason):
        transitions.append(FetchTransition(source, target, reason))
