from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from se_kb_app.artifacts.models import ExtractionOutcome, OutcomeTag, ProcessingTrace
from se_kb_app.errors import ApplicationError, ErrorKind
from se_kb_app.extraction.cleaning import CleanDocument
from se_kb_app.extraction.context import ContextSelector
from se_kb_app.extraction.structured import Repair, StructuredExtractionResult, StructuredExtractor
from se_kb_app.observability import METRICS


ModelCall = Callable[[str, int], str]


@dataclass(frozen=True)
class ExtractionAttemptResult:
    result: StructuredExtractionResult
    selected_chars: int


class ExtractionCoordinator:
    def __init__(
        self,
        selector: ContextSelector,
        extractor: StructuredExtractor,
        model: ModelCall,
        *,
        estimated_cost_per_million_tokens: float = 0.0,
    ) -> None:
        self.selector = selector
        self.extractor = extractor
        self.model = model
        self.estimated_cost_per_million_tokens = estimated_cost_per_million_tokens

    def run(
        self,
        document: CleanDocument,
        *,
        artifact_type: str,
        trace: ProcessingTrace,
        repair: Repair | None = None,
    ) -> ExtractionAttemptResult:
        started = perf_counter()
        if not document.text.strip():
            completed = ExtractionAttemptResult(
                StructuredExtractionResult(
                    ExtractionOutcome(OutcomeTag.NO_KNOWLEDGE), None, trace, 0
                ),
                0,
            )
            self._record(completed, started)
            return completed
        context = self.selector.select(document, artifact_type=artifact_type)
        METRICS.increment(
            "llm_input_tokens_total",
            value=max(1, len(context.prompt_data) // 4),
            stage="extraction",
        )
        model_started = perf_counter()
        try:
            raw = self.model(context.prompt_data, context.output_token_budget)
            output_tokens = max(1, len(raw) // 4)
            input_tokens = max(1, len(context.prompt_data) // 4)
            METRICS.increment("llm_output_tokens_total", value=output_tokens, stage="extraction")
            METRICS.observe(
                "llm_estimated_cost",
                (input_tokens + output_tokens) / 1_000_000 * self.estimated_cost_per_million_tokens,
                stage="extraction",
            )
            METRICS.observe("llm_latency_ms", (perf_counter() - model_started) * 1000, outcome="success")
        except ApplicationError as error:
            tag = {
                ErrorKind.CANCELLATION: OutcomeTag.CANCELLED,
                ErrorKind.POLICY: OutcomeTag.POLICY_FAILED,
            }.get(error.kind, OutcomeTag.DEPENDENCY_FAILED)
            completed = ExtractionAttemptResult(
                StructuredExtractionResult(
                    ExtractionOutcome(tag, diagnostics=(error.public_code,)), None, trace, 1
                ),
                context.selected_chars,
            )
            METRICS.observe("llm_latency_ms", (perf_counter() - model_started) * 1000, outcome=tag.value)
            self._record(completed, started)
            return completed
        except Exception as error:
            completed = ExtractionAttemptResult(
                StructuredExtractionResult(
                    ExtractionOutcome(
                        OutcomeTag.DEPENDENCY_FAILED,
                        diagnostics=(f"model:{type(error).__name__}",),
                    ),
                    None,
                    trace,
                    1,
                ),
                context.selected_chars,
            )
            METRICS.observe("llm_latency_ms", (perf_counter() - model_started) * 1000, outcome="dependency_failed")
            self._record(completed, started)
            return completed
        result = self.extractor.parse(raw, trace=trace, repair=repair)
        completed = ExtractionAttemptResult(result, context.selected_chars)
        self._record(completed, started)
        return completed

    @staticmethod
    def _record(completed: ExtractionAttemptResult, started: float) -> None:
        outcome = completed.result.outcome.tag.value
        METRICS.increment("extraction_outcomes_total", outcome=outcome)
        METRICS.increment("schema_validation_attempts_total", value=completed.result.attempts, outcome=outcome)
        METRICS.observe("stage_duration_ms", (perf_counter() - started) * 1000, stage="extraction", outcome=outcome)
