"""Bounded robots cache for automatic batches; unknown policy fails closed."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
import re

from se_kb_app.domain import FetchRequest, Fetcher
from se_kb_app.errors import ApplicationError, ErrorKind


class SitePolicy:
    def __init__(self, fetcher: Fetcher, *, maximum_entries: int = 128, ttl: float = 300) -> None:
        self.fetcher, self.maximum_entries, self.ttl = fetcher, maximum_entries, ttl
        self._cache: OrderedDict[str, tuple[float, RobotFileParser | None]] = OrderedDict()
        self._lock = Lock()

    def check(self, request: FetchRequest) -> float:
        parsed = urlsplit(request.url)
        origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        with self._lock:
            entry = self._cache.get(origin)
        if entry is None or entry[0] <= monotonic():
            candidate = RobotFileParser(origin + "/robots.txt")
            parser: RobotFileParser | None = candidate
            try:
                document = self.fetcher.fetch(replace(request, url=origin + "/robots.txt", automatic=False))
                final = urlsplit(document.url)
                if (final.scheme, final.netloc) != (parsed.scheme, parsed.netloc):
                    raise ApplicationError(ErrorKind.POLICY, "robots_unknown", "Robots policy is unknown.")
                if re.search(r"<\s*(?:!doctype|html|head|body|script|form)\b", document.content, re.IGNORECASE):
                    raise ApplicationError(ErrorKind.POLICY, "robots_unknown", "Robots endpoint returned an HTML page.")
                candidate.parse(document.content.splitlines())
            except ApplicationError as error:
                status = error.metadata.get("status")
                if status in {404, 410}:
                    candidate.parse(["User-agent: *", "Allow: /"])
                elif status in {401, 403}:
                    candidate.parse(["User-agent: *", "Disallow: /"])
                else:
                    parser = None
            with self._lock:
                self._cache[origin] = (monotonic() + self.ttl, parser)
                self._cache.move_to_end(origin)
                while len(self._cache) > self.maximum_entries:
                    self._cache.popitem(last=False)
        else:
            parser = entry[1]
        if parser is None:
            raise ApplicationError(ErrorKind.POLICY, "robots_unknown", "Robots policy is unknown.")
        agent = "SE-KB-Engine"
        if not parser.can_fetch(agent, request.url):
            raise ApplicationError(ErrorKind.POLICY, "robots_disallowed", "Robots policy disallows this page.")
        delay = float(parser.crawl_delay(agent) or 0)
        rate = parser.request_rate(agent)
        if rate and rate.requests:
            delay = max(delay, rate.seconds / rate.requests)
        return delay
