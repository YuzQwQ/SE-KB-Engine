"""Cooperative stage checkpoints independent of Flask/MCP adapters."""
from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager

from se_kb_app.domain import Cancellation

current_cancellation: ContextVar[Cancellation | None] = ContextVar("job_cancellation", default=None)


def checkpoint() -> None:
    token = current_cancellation.get()
    if token is not None:
        token.checkpoint()


@contextmanager
def publication(cancellation: Cancellation | None = None):
    token = cancellation or current_cancellation.get()
    guard = getattr(token, "publication", None)
    if callable(guard):
        with guard():
            yield
    else:
        if token:
            token.checkpoint()
        yield
