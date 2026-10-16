from __future__ import annotations

import re
from dataclasses import dataclass, replace
from threading import Lock
from collections import OrderedDict
from time import monotonic
from http.cookies import SimpleCookie
from urllib.parse import unquote_plus, urlsplit, urlunsplit

import httpx

from se_kb_app.domain import FetchRequest, FetchedDocument
from se_kb_app.errors import ErrorKind, wrap_error
from se_kb_app.observability import METRICS
from service_boundary.decoding import decode_payload
from service_boundary.transport import VerifiedHTTPTransport, stateless_cookie_jar
from service_boundary.errors import PublicError
from service_boundary.fetch import FetchLimits, URLValidator, bounded_get
from service_boundary.url_policy import Resolver, system_resolver


TRACKING_PARAMETERS = {"fbclid", "gclid", "msclkid", "utm_campaign", "utm_medium", "utm_source", "utm_term", "utm_content"}


@dataclass(frozen=True)
class ConditionalMetadata:
    etag: str | None = None
    last_modified: str | None = None
    document: FetchedDocument | None = None
    expires: float = 0


class RequestMetadataCache:
    def __init__(self, *, maximum_entries: int = 128, ttl_seconds: float = 300) -> None:
        self._metadata: OrderedDict[str, ConditionalMetadata] = OrderedDict()
        self._lock = Lock()
        self.maximum_body_bytes = 16 * 1024 * 1024
        self.maximum_entries, self.ttl_seconds = maximum_entries, ttl_seconds

    def get(self, url: str) -> ConditionalMetadata | None:
        key = canonical_url(url)
        with self._lock:
            metadata = self._metadata.get(key)
            if metadata is not None and metadata.expires <= monotonic():
                self._metadata.pop(key, None)
                metadata = None
            if metadata is not None:
                self._metadata.move_to_end(key)
            return metadata

    def headers_for(self, url: str) -> dict[str, str]:
        metadata = self.get(url)
        headers: dict[str, str] = {}
        if metadata and metadata.document is not None:
            if metadata.etag:
                headers["If-None-Match"] = metadata.etag
            if metadata.last_modified:
                headers["If-Modified-Since"] = metadata.last_modified
        return headers

    def record(self, requested_url: str, final_url: str, headers: httpx.Headers,
               document: FetchedDocument | None = None) -> bool:
        keys = {canonical_url(requested_url), canonical_url(final_url)}
        metadata = ConditionalMetadata(headers.get("etag"), headers.get("last-modified"),
                                       document, monotonic() + self.ttl_seconds)
        with self._lock:
            duplicate = canonical_url(final_url) in self._metadata
            for key in keys:
                self._metadata[key] = metadata
                self._metadata.move_to_end(key)
            while (len(self._metadata) > self.maximum_entries or
                   sum(len(item.document.payload) + len(item.document.content.encode("utf-8"))
                       for item in self._metadata.values() if item.document is not None) > self.maximum_body_bytes):
                self._metadata.popitem(last=False)
        return duplicate


def canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    # Preserve path case, blanks, repeated-parameter order and signed query bytes.
    query = "&".join(part for part in parsed.query.split("&")
                     if part and unquote_plus(part.split("=", 1)[0]).lower() not in TRACKING_PARAMETERS)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").encode("idna").decode("ascii").lower()
    host = f"[{host}]" if ":" in host else host
    port = parsed.port
    netloc = host if port is None or (scheme, port) in {("http", 80), ("https", 443)} else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parsed.path or "/", query, ""))


class PooledHttpFetcher:
    def __init__(
        self,
        *,
        limits: FetchLimits | None = None,
        resolver: Resolver = system_resolver,
        metadata: RequestMetadataCache | None = None,
        max_connections: int = 20,
        max_keepalive_connections: int = 10,
        url_validator: URLValidator | None = None,
        conditional_requests: bool = False,
    ) -> None:
        self.limits = limits or FetchLimits.from_environment()
        self.resolver = resolver
        self.metadata = metadata or RequestMetadataCache()
        self.url_validator = url_validator
        self.conditional_requests = conditional_requests
        pool_limits = httpx.Limits(max_connections=max_connections, max_keepalive_connections=max_keepalive_connections)
        self.client = httpx.Client(
            trust_env=False, cookies=stateless_cookie_jar(),
            headers={"User-Agent": "SE-KB-Engine/0.1", "Accept-Encoding": "gzip, deflate"},
            transport=VerifiedHTTPTransport(limits=pool_limits),
            timeout=self.limits.timeout(),
            follow_redirects=False,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
        )

    def configure_policy(self, policy) -> None:
        self.limits = replace(self.limits, connect_seconds=min(self.limits.connect_seconds, policy.connect_timeout_seconds),
                              read_seconds=min(self.limits.read_seconds, policy.read_timeout_seconds),
                              total_seconds=min(self.limits.total_seconds, policy.total_timeout_seconds),
                              decompressed_bytes=min(self.limits.decompressed_bytes, policy.maximum_body_bytes))

    def fetch(self, request: FetchRequest) -> FetchedDocument:
        headers = {**request.headers}
        if request.cookies:
            jar = SimpleCookie()
            for name, value in request.cookies.items():
                jar[name] = value
            headers["Cookie"] = jar.output(header="", sep=";").strip()
        # Never reuse a personalized representation for another credential scope.
        cacheable = not request.headers and not request.cookies
        if self.conditional_requests and cacheable:
            headers.update(self.metadata.headers_for(request.url))
        network_started = monotonic()
        try:
            response, payload = bounded_get(
                self.client,
                request.url,
                limits=self.limits,
                resolver=self.resolver,
                headers=headers,
                deadline=request.deadline,
                checkpoint=request.cancellation.checkpoint if request.cancellation else None,
                request_scope=request.request_scope,
                url_validator=self.url_validator,
            )
        except PublicError as error:
            raise wrap_error(
                ErrorKind.POLICY,
                error.code,
                "The response violated fetch policy.",
                retryable=False,
                cause=error,
                metadata={"url": request.url},
            ) from error
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            retryable = status in {408, 425, 429} or 500 <= status < 600
            raise wrap_error(
                ErrorKind.NETWORK,
                "transient_http_status" if retryable else "permanent_http_status",
                "The upstream returned an unsuccessful status.",
                retryable=retryable,
                cause=error,
                metadata={"status": status, "retry_after": error.response.headers.get("retry-after")},
            ) from error
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as error:
            raise wrap_error(
                ErrorKind.NETWORK,
                "transient_transport_failure",
                "The upstream connection failed.",
                retryable=True,
                cause=error,
                metadata={"url": request.url},
            ) from error
        finally:
            METRICS.observe("stage_duration_ms", (monotonic() - network_started) * 1000, stage="http_acquisition")
        if response.status_code in {204, 205}:
            raise wrap_error(ErrorKind.NETWORK, "upstream_no_content", "The upstream has no page content.",
                             retryable=False, cause=ValueError("empty status"))
        if response.status_code == 304:
            cached = self.metadata.get(request.url) if cacheable else None
            if cached is None or cached.document is None:
                raise wrap_error(ErrorKind.NETWORK, "conditional_body_missing", "No cached body is available.",
                                 retryable=False, cause=ValueError("unsolicited 304"))
            return replace(cached.document, metadata={**cached.document.metadata, "not_modified": True})
        media_type = response.headers.get("content-type", "text/html").split(";", 1)[0].strip().lower()
        content, encoding, replacements = decode_payload(payload, response.headers.get("content-type", ""))
        title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
        document = FetchedDocument(str(response.url), title, content, media_type,
                                   request.url, response.status_code, encoding, payload,
                                   {"replacement_ratio": replacements, "network_elapsed_seconds": monotonic() - network_started,
                                    "raw_bytes": response.extensions.get("raw_bytes", len(payload)),
                                    "decoded_bytes": len(payload)})
        cache_control = response.headers.get("cache-control", "").lower()
        if cacheable and not response.headers.get("set-cookie") and not any(
            value in cache_control for value in ("no-store", "private")
        ):
            self.metadata.record(request.url, str(response.url), response.headers, document if self.conditional_requests else None)
        return document

    def close(self) -> None:
        self.client.close()
