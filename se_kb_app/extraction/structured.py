from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import jsonschema

from se_kb_app.artifacts.models import ExtractionOutcome, OutcomeTag, ProcessingTrace


FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)
HARMLESS_PREFIX = re.compile(r"^\s*(?:here is (?:the )?json\s*:?|result\s*:)\s*", re.IGNORECASE)


@dataclass(frozen=True)
class StructuredExtractionResult:
    outcome: ExtractionOutcome
    value: Mapping[str, Any] | None
    trace: ProcessingTrace
    attempts: int


Repair = Callable[[str, tuple[str, ...], int], str]


class StructuredExtractor:
    def __init__(self, schema: Mapping[str, Any], *, maximum_repairs: int = 1) -> None:
        if maximum_repairs < 0 or maximum_repairs > 3:
            raise ValueError("maximum_repairs must be between 0 and 3")
        self.schema = dict(schema)
        self.maximum_repairs = maximum_repairs
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def parse(self, raw: str, *, trace: ProcessingTrace, repair: Repair | None = None) -> StructuredExtractionResult:
        diagnostics: list[str] = []
        candidate = raw
        for attempt in range(self.maximum_repairs + 1):
            try:
                value = parse_json_object(candidate)
                errors = sorted(self.validator.iter_errors(value), key=lambda error: list(error.path))
                if not errors:
                    artifact_identifier = str(value.get("id", "validated-artifact"))
                    return StructuredExtractionResult(
                        ExtractionOutcome(OutcomeTag.SUCCESS, (artifact_identifier,)),
                        value,
                        trace,
                        attempt + 1,
                    )
                diagnostics.extend(_validation_diagnostic(error) for error in errors)
            except (UnicodeError, ValueError, json.JSONDecodeError) as error:
                diagnostics.append(f"parse:{type(error).__name__}")
            if attempt >= self.maximum_repairs or repair is None:
                break
            candidate = repair(candidate, tuple(diagnostics), attempt + 1)
        bounded = tuple(diagnostics[:100])
        return StructuredExtractionResult(
            ExtractionOutcome(OutcomeTag.VALIDATION_FAILED, diagnostics=bounded),
            None,
            trace,
            min(self.maximum_repairs + 1, len(diagnostics) + 1),
        )


def parse_json_object(raw: str) -> Mapping[str, Any]:
    raw.encode("utf-8", errors="strict")
    match = FENCE.fullmatch(raw)
    candidate = match.group(1) if match else HARMLESS_PREFIX.sub("", raw, count=1)
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("model output must be a JSON object")
    return value


def _validation_diagnostic(error: jsonschema.ValidationError) -> str:
    path = "/".join(str(part) for part in error.absolute_path) or "$"
    return f"schema:{path}:{error.validator}"
