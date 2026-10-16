"""Deprecated rendering facade; uses the same safe acquisition service as entrypoints."""
from __future__ import annotations

import logging
from time import monotonic

from se_kb_app.domain import FetchRequest
from se_kb_app.errors import ApplicationError

logger = logging.getLogger(__name__)


def fetch_rendered_html_sync(url: str, timeout_ms: int = 30000,
                             human_simulation: bool = False, proxy_server: str | None = None) -> str | None:
    """HTTP-first compatibility call. Legacy human simulation is intentionally ignored."""
    if proxy_server:
        logger.warning("Selected proxy has no verified rendering adapter.")
        return None
    from se_kb_app.crawling.runtime import default_crawl_service
    try:
        return default_crawl_service().fetch(FetchRequest(url,
            deadline=monotonic() + max(1, timeout_ms) / 1000)).content
    except ApplicationError as error:
        logger.warning("Page acquisition failed: %s", error.public_code)
        return None
