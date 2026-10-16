from __future__ import annotations

from se_kb_app.errors import ApplicationError


def should_retry(error: BaseException) -> bool:
    """Retry only errors explicitly classified as retryable."""
    return isinstance(error, ApplicationError) and error.retryable
