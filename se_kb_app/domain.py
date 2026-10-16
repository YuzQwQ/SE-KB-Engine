from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence
from collections.abc import Callable
from contextlib import AbstractContextManager
from types import MappingProxyType


@dataclass(frozen=True)
class SearchRequest:
    query: str
    limit: int
    engine: str | None = None


@dataclass(frozen=True)
class SearchHit:
    url: str
    title: str = ""
    score: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FetchRequest:
    url: str
    save: bool = False
    deadline: float | None = None
    cancellation: Cancellation | None = None
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)
    cookies: Mapping[str, str] = field(default_factory=dict, repr=False)
    automatic: bool = False
    maximum_attempts: int = 3
    request_scope: Callable[[str], AbstractContextManager[None]] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.maximum_attempts) is not int or not 1 <= self.maximum_attempts <= 3:
            raise ValueError("maximum_attempts must be between 1 and 3")
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))
        object.__setattr__(self, "cookies", MappingProxyType(dict(self.cookies)))


@dataclass(frozen=True)
class FetchedDocument:
    url: str
    title: str
    content: str
    media_type: str = "text/html"
    requested_url: str = ""
    status_code: int = 200
    encoding: str = "utf-8"
    payload: bytes = field(default=b"", repr=False)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionRequest:
    content: str
    source_url: str = ""
    title: str = ""
    types: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractionResult:
    artifacts: tuple[Mapping[str, Any], ...]
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoredArtifact:
    identifier: str
    path: Path


@dataclass(frozen=True)
class RetrievalRequest:
    query: str
    top_k: int = 5
    intent: str | None = None


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    intent: str
    items: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class JobReference:
    identifier: str
    status: str


@dataclass(frozen=True)
class DomainEvent:
    name: str
    occurred_at: datetime
    payload: Mapping[str, Any] = field(default_factory=dict)


class SearchService(Protocol):
    def search(self, request: SearchRequest) -> Sequence[SearchHit]: ...


class Fetcher(Protocol):
    def fetch(self, request: FetchRequest) -> FetchedDocument: ...
    def close(self) -> None: ...


class Extractor(Protocol):
    def extract(self, request: ExtractionRequest) -> ExtractionResult: ...


class ArtifactStore(Protocol):
    def save(self, result: ExtractionResult) -> Sequence[StoredArtifact]: ...
    def close(self) -> None: ...


class Retriever(Protocol):
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult: ...
    def close(self) -> None: ...


class JobRunner(Protocol):
    def submit(self, operation: str, payload: Mapping[str, Any]) -> JobReference: ...
    def close(self) -> None: ...


class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def close(self) -> None: ...


class Cancellation(Protocol):
    @property
    def cancelled(self) -> bool: ...
    def checkpoint(self) -> None: ...
