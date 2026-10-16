"""HTTPX transport seam: retain origin/TLS pooling, connect only to validated IPs.

HTTPX exposes no network-backend constructor argument. The single private backend
assignment below is covered by transport tests; all request/stream APIs stay public.
"""
from __future__ import annotations

from contextvars import ContextVar
from time import monotonic
from typing import Any, cast
from http.cookiejar import CookieJar, DefaultCookiePolicy

import httpx

from service_boundary.errors import public_error

_context: ContextVar[dict[str, Any]] = ContextVar("fetch_transport", default={})


class _NoAmbientCookies(DefaultCookiePolicy):
    def set_ok(self, cookie, request):
        return False

    def return_ok(self, cookie, request):
        return False


def stateless_cookie_jar() -> CookieJar:
    """Shared transports must not retain personalized page sessions across jobs."""
    return CookieJar(policy=_NoAmbientCookies())


def _timeout(timeout: float | None) -> float | None:
    deadline = _context.get().get("fetch_deadline")
    if deadline is None:
        return timeout
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise httpx.ReadTimeout("Fetch deadline exceeded.")
    return min(timeout, remaining) if timeout is not None else remaining


class _Stream:
    def __init__(self, stream: Any) -> None:
        self.stream = stream

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return self.stream.read(max_bytes, timeout=_timeout(timeout))

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        self.stream.write(buffer, timeout=_timeout(timeout))

    def start_tls(self, ssl_context: Any, server_hostname: str | None = None,
                  timeout: float | None = None) -> "_Stream":
        return _Stream(self.stream.start_tls(ssl_context, server_hostname, _timeout(timeout)))

    def close(self) -> None:
        self.stream.close()

    def get_extra_info(self, info: str) -> Any:
        return self.stream.get_extra_info(info)


class _Backend:
    def __init__(self, backend: Any) -> None:
        self.backend = backend

    def connect_tcp(self, host: str, port: int, timeout: float | None = None,
                    local_address: str | None = None, socket_options: Any = None) -> _Stream:
        target = _context.get().get("validated_target")
        if target is None or target.host != host or target.port != port:
            raise public_error("url_not_allowed")
        last_error: OSError | Exception = OSError("No permitted address.")
        for address in target.addresses:
            try:
                return _Stream(self.backend.connect_tcp(
                    str(address), port, timeout=_timeout(timeout),
                    local_address=local_address, socket_options=socket_options,
                ))
            except Exception as error:
                last_error = error
        raise last_error

    def connect_unix_socket(self, *args: Any, **kwargs: Any) -> Any:
        raise public_error("url_not_allowed")

    def sleep(self, seconds: float) -> None:
        self.backend.sleep(seconds)


class _ScopedBody(httpx.SyncByteStream):
    def __init__(self, stream: httpx.SyncByteStream, context: dict[str, Any]) -> None:
        self.stream, self.context = stream, context

    def __iter__(self):
        token = _context.set(self.context)
        try:
            yield from self.stream
        finally:
            _context.reset(token)

    def close(self) -> None:
        self.stream.close()


class VerifiedHTTPTransport(httpx.HTTPTransport):
    def __init__(self, *, limits: httpx.Limits | None = None) -> None:
        super().__init__(trust_env=False, limits=limits or httpx.Limits())
        cast(Any, self._pool)._network_backend = _Backend(self._pool._network_backend)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        context = dict(request.extensions)
        token = _context.set(context)
        try:
            response = super().handle_request(request)
            assert isinstance(response.stream, httpx.SyncByteStream)
            response.stream = _ScopedBody(response.stream, context)
            return response
        finally:
            _context.reset(token)


class _AsyncStream:
    def __init__(self, stream: Any) -> None:
        self.stream = stream

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return await self.stream.read(max_bytes, timeout=_timeout(timeout))

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        await self.stream.write(buffer, timeout=_timeout(timeout))

    async def start_tls(self, ssl_context: Any, server_hostname: str | None = None,
                        timeout: float | None = None) -> "_AsyncStream":
        return _AsyncStream(await self.stream.start_tls(ssl_context, server_hostname, _timeout(timeout)))

    async def aclose(self) -> None:
        await self.stream.aclose()

    def get_extra_info(self, info: str) -> Any:
        return self.stream.get_extra_info(info)


class _AsyncBackend:
    def __init__(self, backend: Any) -> None:
        self.backend = backend

    async def connect_tcp(self, host: str, port: int, timeout: float | None = None,
                          local_address: str | None = None, socket_options: Any = None) -> _AsyncStream:
        target = _context.get().get("validated_target")
        if target is None or target.host != host or target.port != port:
            raise public_error("url_not_allowed")
        last_error: Exception = OSError("No permitted address.")
        for address in target.addresses:
            try:
                return _AsyncStream(await self.backend.connect_tcp(
                    str(address), port, timeout=_timeout(timeout), local_address=local_address,
                    socket_options=socket_options))
            except Exception as error:
                last_error = error
        raise last_error

    async def connect_unix_socket(self, *args: Any, **kwargs: Any) -> Any:
        raise public_error("url_not_allowed")

    async def sleep(self, seconds: float) -> None:
        await self.backend.sleep(seconds)


class _ScopedAsyncBody(httpx.AsyncByteStream):
    def __init__(self, stream: httpx.AsyncByteStream, context: dict[str, Any]) -> None:
        self.stream, self.context = stream, context

    async def __aiter__(self):
        token = _context.set(self.context)
        try:
            async for chunk in self.stream:
                yield chunk
        finally:
            _context.reset(token)

    async def aclose(self) -> None:
        await self.stream.aclose()


class VerifiedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    def __init__(self) -> None:
        super().__init__(trust_env=False)
        cast(Any, self._pool)._network_backend = _AsyncBackend(self._pool._network_backend)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        context = dict(request.extensions)
        token = _context.set(context)
        try:
            response = await super().handle_async_request(request)
            assert isinstance(response.stream, httpx.AsyncByteStream)
            response.stream = _ScopedAsyncBody(response.stream, context)
            return response
        finally:
            _context.reset(token)
