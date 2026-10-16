from __future__ import annotations

import os
import asyncio
import zlib
import math
from contextlib import nullcontext
import time
from dataclasses import dataclass
from typing import Callable
from collections.abc import Mapping

import httpx
from PIL import Image
from io import BytesIO

from service_boundary.errors import public_error
from service_boundary.url_policy import Resolver, ValidatedURL, system_resolver, validate_url

from service_boundary.resolution import bounded_validation

URLValidator = Callable[[str], ValidatedURL]


@dataclass(frozen=True)
class FetchLimits:
    redirects: int = 5
    compressed_bytes: int = 8 * 1024 * 1024
    decompressed_bytes: int = 16 * 1024 * 1024
    image_pixels: int = 40_000_000
    total_seconds: float = 60.0
    connect_seconds: float = 10.0
    read_seconds: float = 20.0
    write_seconds: float = 20.0
    pool_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.redirects < 0 or min(self.compressed_bytes, self.decompressed_bytes, self.image_pixels) < 1:
            raise ValueError("Fetch byte and redirect limits are invalid.")
        values = (self.total_seconds, self.connect_seconds, self.read_seconds, self.write_seconds, self.pool_seconds)
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError("Fetch timeouts must be finite and positive.")

    @classmethod
    def from_environment(cls) -> "FetchLimits":
        defaults = cls()

        def integer(name: str, default: int) -> int:
            try:
                return max(1, int(os.getenv(name, str(default))))
            except ValueError:
                return default

        return cls(
            redirects=integer("FETCH_MAX_REDIRECTS", defaults.redirects),
            compressed_bytes=integer("FETCH_MAX_COMPRESSED_BYTES", defaults.compressed_bytes),
            decompressed_bytes=integer("FETCH_MAX_DECOMPRESSED_BYTES", defaults.decompressed_bytes),
            image_pixels=integer("FETCH_MAX_IMAGE_PIXELS", defaults.image_pixels),
            total_seconds=float(os.getenv("FETCH_TOTAL_SECONDS", defaults.total_seconds)),
            connect_seconds=float(os.getenv("FETCH_CONNECT_SECONDS", defaults.connect_seconds)),
            read_seconds=float(os.getenv("FETCH_READ_SECONDS", defaults.read_seconds)),
            write_seconds=float(os.getenv("FETCH_WRITE_SECONDS", defaults.write_seconds)),
            pool_seconds=float(os.getenv("FETCH_POOL_SECONDS", defaults.pool_seconds)),
        )

    def timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_seconds,
            read=self.read_seconds,
            write=self.write_seconds,
            pool=self.pool_seconds,
        )


def _origin(url: str) -> tuple[str, str, int]:
    parsed = httpx.URL(url)
    return parsed.scheme, parsed.host, parsed.port or (443 if parsed.scheme == "https" else 80)


def _request(client, target, initial_url, headers, policy, deadline, clock):
    remaining = deadline - clock()
    if remaining <= 0:
        raise public_error("resource_limit")
    timeout = httpx.Timeout(
        connect=min(policy.connect_seconds, remaining), read=min(policy.read_seconds, remaining),
        write=min(policy.write_seconds, remaining), pool=min(policy.pool_seconds, remaining),
    )
    request = client.build_request("GET", target.url, headers=headers, timeout=timeout)
    # Build first, then strip: client defaults and domainless cookie jars otherwise
    # silently add credentials back to a manually followed redirect.
    if _origin(target.url) != _origin(initial_url):
        for name in list(request.headers):
            if name.lower() not in {"host", "accept", "accept-encoding", "accept-language", "user-agent", "connection"}:
                del request.headers[name]
    request.extensions.update(validated_target=target, fetch_deadline=deadline)
    return request


def _check_headers(response, policy, allowed_media_types):
    if response.status_code != 304:
        response.raise_for_status()
    media = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media and not any(media == value or media.startswith(value + "/") for value in allowed_media_types):
        raise public_error("resource_limit")
    declared = response.headers.get("content-length")
    if declared:
        try:
            if int(declared) < 0 or int(declared) > policy.compressed_bytes:
                raise public_error("resource_limit")
        except ValueError as error:
            raise public_error("resource_limit") from error


class _BodyDecoder:
    def __init__(self, response, policy):
        self.policy = policy
        self.raw = self.decoded = 0
        encoding = response.headers.get("content-encoding", "identity").strip().lower()
        self.encoding = encoding
        if encoding not in {"identity", "", "gzip", "deflate"}:
            raise public_error("resource_limit")
        self.decoder = zlib.decompressobj(16 + zlib.MAX_WBITS if encoding == "gzip" else zlib.MAX_WBITS) if encoding in {"gzip", "deflate"} else None
        self.probe = bytearray()
        self.deflate_ready = encoding != "deflate"

    def feed(self, chunk):
        self.raw += len(chunk)
        if self.raw > self.policy.compressed_bytes:
            raise public_error("resource_limit")
        if not self.deflate_ready:
            self.probe.extend(chunk)
            if len(self.probe) < 2:
                return b""
            first, second = self.probe[:2]
            zlib_header = first & 15 == 8 and (first * 256 + second) % 31 == 0
            self.decoder = zlib.decompressobj(zlib.MAX_WBITS if zlib_header else -zlib.MAX_WBITS)
            chunk = bytes(self.probe)
            self.probe.clear()
            self.deflate_ready = True
        remaining = self.policy.decompressed_bytes - self.decoded
        try:
            if self.decoder is not None:
                output = self.decoder.decompress(chunk, remaining + 1)
                if self.decoder.unconsumed_tail:
                    raise public_error("resource_limit")
            else:
                output = chunk
        except zlib.error as error:
            raise public_error("resource_limit") from error
        self.decoded += len(output)
        if self.decoded > self.policy.decompressed_bytes:
            raise public_error("resource_limit")
        return output

    def finish(self):
        if self.decoder is not None and (not self.decoder.eof or self.decoder.unused_data):
            raise public_error("resource_limit")


def _already_buffered(response, policy):
    # MockTransport and explicitly buffered responses already ran HTTPX decoding.
    payload = response.content
    if len(payload) > policy.decompressed_bytes:
        raise public_error("resource_limit")
    if not response.headers.get("content-encoding") and len(payload) > policy.compressed_bytes:
        raise public_error("resource_limit")
    return payload


def bounded_get(
    client: httpx.Client,
    url: str,
    *,
    limits: FetchLimits | None = None,
    resolver: Resolver = system_resolver,
    allowed_media_types: tuple[str, ...] = ("text/html", "text/plain", "application/xhtml+xml"),
    clock: Callable[[], float] = time.monotonic,
    headers: Mapping[str, str] | None = None,
    url_validator: URLValidator | None = None,
    deadline: float | None = None,
    checkpoint: Callable[[], None] | None = None,
    request_scope=None,
    follow_redirects: bool = True,
) -> tuple[httpx.Response, bytes]:
    policy = limits or FetchLimits.from_environment()
    end = min(deadline if deadline is not None else float("inf"), clock() + policy.total_seconds)
    validate = url_validator or (lambda value: validate_url(value, resolver=resolver))
    def target_for(value):
        if checkpoint:
            checkpoint()
        # Explicit test validators/resolvers stay synchronous and deterministic.
        return validate(value) if url_validator or resolver is not system_resolver else bounded_validation(validate, value, end)
    target = target_for(url)
    for hop in range(policy.redirects + 1):
        if checkpoint:
            checkpoint()
        request = _request(client, target, url, headers, policy, end, clock)
        with request_scope(target.url) if request_scope else nullcontext():
            response = client.send(request, stream=True, follow_redirects=False, auth=None)
            try:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if hop >= policy.redirects or not response.headers.get("location"):
                        raise public_error("resource_limit")
                    target = target_for(str(httpx.URL(target.url).join(response.headers["location"])))
                    if not follow_redirects:
                        return response, b""
                    continue
                _check_headers(response, policy, allowed_media_types)
                if response.status_code == 304:
                    return response, b""
                if response.is_stream_consumed:
                    payload = _already_buffered(response, policy)
                else:
                    decoder = _BodyDecoder(response, policy)
                    chunks = bytearray()
                    for chunk in response.iter_raw():
                        if checkpoint:
                            checkpoint()
                        if clock() >= end:
                            raise public_error("resource_limit")
                        chunks.extend(decoder.feed(chunk))
                    decoder.finish()
                    payload = bytes(chunks)
                    response.extensions.update(raw_bytes=decoder.raw, decoded_bytes=decoder.decoded)
                if clock() >= end:
                    raise public_error("resource_limit")
                return response, payload
            finally:
                response.close()
    raise public_error("resource_limit")


async def bounded_async_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    limits: FetchLimits | None = None,
    resolver: Resolver = system_resolver,
    allowed_media_types: tuple[str, ...] = ("text/html", "text/plain", "application/xhtml+xml"),
    clock: Callable[[], float] = time.monotonic,
    headers: Mapping[str, str] | None = None,
    url_validator: URLValidator | None = None,
    deadline: float | None = None,
    checkpoint: Callable[[], None] | None = None,
) -> tuple[httpx.Response, bytes]:
    policy = limits or FetchLimits.from_environment()
    end = min(deadline if deadline is not None else float("inf"), clock() + policy.total_seconds)
    validate = url_validator or (lambda value: validate_url(value, resolver=resolver))
    async def target_for(value):
        if checkpoint:
            checkpoint()
        if url_validator or resolver is not system_resolver:
            return validate(value)
        return await asyncio.to_thread(bounded_validation, validate, value, end)
    async with asyncio.timeout(max(0, end - clock())):
        target = await target_for(url)
        for hop in range(policy.redirects + 1):
            if checkpoint:
                checkpoint()
            request = _request(client, target, url, headers, policy, end, clock)
            response = await client.send(request, stream=True, follow_redirects=False, auth=None)
            try:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if hop >= policy.redirects or not response.headers.get("location"):
                        raise public_error("resource_limit")
                    target = await target_for(str(httpx.URL(target.url).join(response.headers["location"])))
                    continue
                _check_headers(response, policy, allowed_media_types)
                if response.status_code == 304:
                    return response, b""
                if response.is_stream_consumed:
                    payload = _already_buffered(response, policy)
                else:
                    decoder = _BodyDecoder(response, policy)
                    chunks = bytearray()
                    async for chunk in response.aiter_raw():
                        if checkpoint:
                            checkpoint()
                        if clock() >= end:
                            raise public_error("resource_limit")
                        chunks.extend(decoder.feed(chunk))
                    decoder.finish()
                    payload = bytes(chunks)
                    response.extensions.update(raw_bytes=decoder.raw, decoded_bytes=decoder.decoded)
                return response, payload
            finally:
                await response.aclose()
    raise public_error("resource_limit")


def validate_image_bytes(payload: bytes, *, limits: FetchLimits | None = None) -> tuple[int, int]:
    policy = limits or FetchLimits.from_environment()
    if len(payload) > policy.decompressed_bytes:
        raise public_error("resource_limit")
    try:
        with Image.open(BytesIO(payload)) as image:
            width, height = image.size
            if width < 1 or height < 1 or width * height > policy.image_pixels:
                raise public_error("resource_limit")
            image.verify()
            return width, height
    except Exception as exc:
        if getattr(exc, "code", None) == "resource_limit":
            raise
        raise public_error("resource_limit") from exc
