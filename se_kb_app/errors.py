from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class ErrorKind(str, Enum):
    CONFIGURATION = "configuration"
    AUTHORIZATION = "authorization"
    POLICY = "policy"
    NETWORK = "network"
    PARSING = "parsing"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    STORAGE = "storage"
    RETRIEVAL = "retrieval"
    CANCELLATION = "cancellation"
    INTERNAL = "internal"


@dataclass
class ApplicationError(Exception):
    kind: ErrorKind
    public_code: str
    safe_message: str
    retryable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    cause: BaseException | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.metadata = MappingProxyType(dict(self.metadata))
        super().__init__(self.safe_message)

    def __str__(self) -> str:
        return self.safe_message


def configuration_error(
    setting: str,
    remediation: str,
    *,
    cause: BaseException | None = None,
) -> ApplicationError:
    return ApplicationError(
        kind=ErrorKind.CONFIGURATION,
        public_code="invalid_configuration",
        safe_message=f"Invalid setting '{setting}'. {remediation}",
        retryable=False,
        metadata={"setting": setting, "remediation": remediation},
        cause=cause,
    )


def wrap_error(
    kind: ErrorKind,
    public_code: str,
    safe_message: str,
    *,
    retryable: bool,
    cause: BaseException,
    metadata: Mapping[str, Any] | None = None,
) -> ApplicationError:
    return ApplicationError(
        kind=kind,
        public_code=public_code,
        safe_message=safe_message,
        retryable=retryable,
        metadata=metadata or {},
        cause=cause,
    )
