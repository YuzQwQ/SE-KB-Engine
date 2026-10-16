from __future__ import annotations

from dataclasses import asdict

import pytest

from se_kb_app.artifacts.models import OutcomeTag, ProcessingTrace
from se_kb_app.errors import ApplicationError, ErrorKind
from se_kb_app.extraction.cleaning import CLEANER_VERSION, DeterministicCleaner
from se_kb_app.extraction.context import ContextBudget, ContextSelector
from se_kb_app.extraction.pipeline import ExtractionCoordinator
from se_kb_app.extraction.refinement import deterministic_refine
from se_kb_app.extraction.structured import StructuredExtractor


TRACE = ProcessingTrace("0.1.0", CLEANER_VERSION, "router-v2", "prompt-v3", "model-v4", "params-v2", "schema-v5")
SCHEMA = {
    "type": "object",
    "required": ["id", "name"],
    "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
}


def coordinator(model):
    return ExtractionCoordinator(
        ContextSelector(ContextBudget(maximum_input_chars=1000, maximum_output_tokens=100)),
        StructuredExtractor(SCHEMA, maximum_repairs=0),
        model,
    )


@pytest.mark.unit
def test_extraction_records_every_processing_version_and_success_outcome():
    document = DeterministicCleaner().clean("https://example.com", "<article><p>knowledge body</p></article>")
    result = coordinator(lambda prompt, budget: '{"id":"art_valid","name":"Knowledge"}').run(
        document, artifact_type="concept", trace=TRACE
    )
    assert result.result.outcome.tag is OutcomeTag.SUCCESS
    assert result.result.trace == TRACE
    assert result.selected_chars <= 1000


@pytest.mark.unit
@pytest.mark.parametrize(
    ("error", "tag"),
    [
        (ApplicationError(ErrorKind.POLICY, "blocked", "Blocked."), OutcomeTag.POLICY_FAILED),
        (ApplicationError(ErrorKind.CANCELLATION, "cancelled", "Cancelled."), OutcomeTag.CANCELLED),
        (ApplicationError(ErrorKind.NETWORK, "offline", "Offline."), OutcomeTag.DEPENDENCY_FAILED),
    ],
)
def test_dependency_policy_and_cancelled_outcomes_are_distinct(error, tag):
    document = DeterministicCleaner().clean("https://example.com", "<article><p>knowledge body</p></article>")

    def fail(prompt, budget):
        raise error

    result = coordinator(fail).run(document, artifact_type="concept", trace=TRACE)
    assert result.result.outcome.tag is tag
    assert result.result.value is None


@pytest.mark.unit
def test_empty_and_invalid_outputs_are_not_promoted():
    empty = DeterministicCleaner().clean("https://example.com/empty", "<article></article>")
    no_knowledge = coordinator(lambda prompt, budget: "{}").run(
        empty, artifact_type="concept", trace=TRACE
    )
    assert no_knowledge.result.outcome.tag is OutcomeTag.NO_KNOWLEDGE
    invalid = DeterministicCleaner().clean("https://example.com/invalid", "<p>body content</p>")
    failed = coordinator(lambda prompt, budget: '{"id":"missing-name"}').run(
        invalid, artifact_type="concept", trace=TRACE
    )
    assert failed.result.outcome.tag is OutcomeTag.VALIDATION_FAILED
    assert failed.result.outcome.artifact_ids == ()


@pytest.mark.unit
def test_deterministic_refinement_is_idempotent_and_preserves_provenance_conflicts():
    inputs = [
        {"type": "concept", "key": "Process", "content": {"definition": "B"}, "source_ids": ["doc-2"]},
        {"type": "concept", "key": "process", "content": {"definition": "A"}, "source_ids": ["doc-1"]},
        {"type": "concept", "key": "PROCESS", "content": {"definition": "A"}, "source_ids": ["doc-3"]},
    ]
    first = deterministic_refine(inputs)
    second = deterministic_refine(reversed(inputs))
    third = deterministic_refine(
        {
            "type": item.artifact_type,
            "key": item.key,
            "content": item.content,
            "source_ids": item.source_ids,
            "conflicts": item.conflicts,
        }
        for item in first
    )
    assert [asdict(item) for item in first] == [asdict(item) for item in second]
    assert [asdict(item) for item in third] == [asdict(item) for item in first]
    assert first[0].source_ids == ("doc-1", "doc-2", "doc-3")
    assert first[0].conflicts and first[0].decisions
