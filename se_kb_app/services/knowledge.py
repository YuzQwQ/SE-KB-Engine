from __future__ import annotations

from collections.abc import Callable, Sequence

from se_kb_app.domain import (
    ArtifactStore,
    Cancellation,
    ExtractionRequest,
    ExtractionResult,
    Extractor,
    StoredArtifact,
)
from se_kb_app.errors import ApplicationError, ErrorKind, wrap_error


Validator = Callable[[ExtractionResult], None]
VisualAnalyzer = Callable[[ExtractionRequest], ExtractionRequest]


class KnowledgeOrchestrator:
    def __init__(
        self,
        extractor: Extractor,
        store: ArtifactStore,
        *,
        validator: Validator | None = None,
        visual_analyzer: VisualAnalyzer | None = None,
        cancellation: Cancellation | None = None,
    ) -> None:
        self.extractor = extractor
        self.store = store
        self.validator = validator or (lambda _result: None)
        self.visual_analyzer = visual_analyzer or (lambda request: request)
        self.cancellation = cancellation

    def extract_and_save(self, request: ExtractionRequest) -> tuple[ExtractionResult, Sequence[StoredArtifact]]:
        try:
            if self.cancellation is not None:
                self.cancellation.checkpoint()
            enriched = self.visual_analyzer(request)
            if self.cancellation is not None:
                self.cancellation.checkpoint()
            result = self.extractor.extract(enriched)
            if self.cancellation is not None:
                self.cancellation.checkpoint()
            self.validator(result)
            if self.cancellation is not None:
                self.cancellation.checkpoint()
            return result, self.store.save(result)
        except ApplicationError:
            raise
        except Exception as error:
            raise wrap_error(
                ErrorKind.EXTRACTION,
                "knowledge_processing_failed",
                "Knowledge extraction could not be completed.",
                retryable=False,
                cause=error,
            ) from error

    def close(self) -> None:
        self.store.close()
