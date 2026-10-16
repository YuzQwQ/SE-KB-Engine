"""Bounded DNS admission; callers stop waiting at their operation deadline."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import BoundedSemaphore
from time import monotonic
from typing import Callable

from service_boundary.errors import public_error
from service_boundary.url_policy import ValidatedURL

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="fetch-dns")
_admission = BoundedSemaphore(20)


def bounded_validation(validate: Callable[[str], ValidatedURL], url: str,
                       deadline: float) -> ValidatedURL:
    if not _admission.acquire(blocking=False):
        raise public_error("resource_limit")
    try:
        future = _executor.submit(validate, url)
    except BaseException:
        _admission.release()
        raise
    future.add_done_callback(lambda _: _admission.release())
    try:
        return future.result(timeout=max(0, deadline - monotonic()))
    except TimeoutError as error:
        future.cancel()
        raise public_error("resource_limit") from error
