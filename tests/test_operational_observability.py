from __future__ import annotations

import json
import logging
from io import StringIO

import pytest

from scripts.benchmark_telemetry import benchmark
from se_kb_app.budgets import BudgetEnforcer, BudgetExceeded, RuntimeBudgets
from se_kb_app.observability import (
    EventContext,
    MetricsRegistry,
    StructuredFormatter,
    emit_event,
    event_context,
    redact_text,
    safe_fields,
)


@pytest.mark.security
def test_adversarial_credentials_headers_and_content_are_redacted_and_bounded():
    secret = "sk-super-secret-credential"
    text = redact_text(f"Authorization: Bearer {secret} password=hunter2 token=abc123")
    assert secret not in text
    assert "hunter2" not in text
    assert "abc123" not in text
    fields = safe_fields(
        {
            "Authorization": f"Bearer {secret}",
            "headers": {"Cookie": secret, "X-Safe": "ok"},
            "content": "private page text",
            "long": "x" * 1000,
        },
        secrets=(secret,),
    )
    encoded = json.dumps(fields)
    assert secret not in encoded and "private page text" not in encoded
    assert len(str(fields["long"])) <= 513


@pytest.mark.unit
def test_structured_event_carries_context_without_full_exception_body():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("test.structured")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    with event_context(correlation_id="request-123", job_id="job-123", document_id="doc-123"):
        emit_event(
            logger,
            "stage_failed",
            EventContext(stage="extraction", attempt=2, outcome="validation_failed", duration_ms=3.5),
            error_type="ValidationError",
        )
    payload = json.loads(stream.getvalue())
    assert payload["correlation_id"] == "request-123"
    assert payload["job_id"] == "job-123"
    assert payload["document_id"] == "doc-123"
    assert payload["stage"] == "extraction"
    assert payload["outcome"] == "validation_failed"


@pytest.mark.unit
def test_metric_labels_and_cardinality_are_bounded():
    metrics = MetricsRegistry(maximum_label_values=2)
    for outcome in ("one", "two", "three"):
        metrics.increment("stage_total", stage="crawl", outcome=outcome)
    snapshot = json.dumps(metrics.snapshot())
    assert "__overflow__" in snapshot
    with pytest.raises(ValueError, match="high-cardinality"):
        metrics.increment("bad_total", url="https://private.example/path")


@pytest.mark.unit
def test_budget_exhaustion_emits_metric_and_stops_work(caplog):
    logger = logging.getLogger("test.budget")
    enforcer = BudgetEnforcer(RuntimeBudgets(max_tokens_per_task=10), logger)
    with caplog.at_level(logging.INFO), pytest.raises(BudgetExceeded, match="tokens"):
        enforcer.require(correlation_id="request-budget", name="tokens", observed=11, limit=10)
    assert any(record.getMessage() == "budget_exhausted" for record in caplog.records)


@pytest.mark.unit
def test_runtime_budgets_are_configurable_and_cover_task_dimensions():
    budgets = RuntimeBudgets.from_environment(
        {
            "MAX_REQUEST_CONCURRENCY": "2",
            "MAX_RESPONSE_BYTES": "10",
            "MAX_TOKENS_PER_TASK": "20",
            "MAX_TASK_SECONDS": "3",
            "MAX_QUEUE_DEPTH": "4",
            "MEMORY_WARNING_BYTES": "30",
            "DISK_WARNING_FREE_BYTES": "40",
        }
    )
    assert budgets.max_concurrency == 2
    enforcer = BudgetEnforcer(budgets, logging.getLogger("test.task-budget"))
    with pytest.raises(BudgetExceeded, match="response_bytes"):
        enforcer.check_task(correlation_id="budget-task", response_bytes=11)


@pytest.mark.unit
def test_telemetry_overhead_and_payload_fit_declared_budget():
    report = benchmark(500)
    assert report["passed"] is True
