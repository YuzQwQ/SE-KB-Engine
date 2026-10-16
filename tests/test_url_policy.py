from __future__ import annotations

import httpx
import pytest

from service_boundary.errors import PublicError
from service_boundary.fetch import FetchLimits, bounded_get
from service_boundary.url_policy import parse_http_url, validate_url


def resolver(addresses):
    return lambda _host, _port: addresses


@pytest.mark.unit
@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "https://user:secret@example.com/",
        "https://example.com:70000/",
        "https://example.com/a\nb",
        "//example.com/path",
    ],
)
def test_parser_rejects_prohibited_schemes_credentials_ports_and_syntax(url):
    with pytest.raises(PublicError) as caught:
        parse_http_url(url)
    assert caught.value.code == "url_not_allowed"


@pytest.mark.unit
def test_url_policy_normalizes_idn_and_removes_fragment():
    target = validate_url(
        "HTTPS://例子.测试/path?q=1#fragment",
        resolver=resolver(["93.184.216.34"]),
    )
    assert target.host == "xn--fsqu00a.xn--0zwm56d"
    assert target.url == "https://xn--fsqu00a.xn--0zwm56d/path?q=1"


@pytest.mark.unit
@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "224.0.0.1",
        "0.0.0.0",
        "192.0.2.1",
        "::1",
        "fe80::1",
        "fd00::1",
        "ff02::1",
    ],
)
def test_url_policy_rejects_non_public_ipv4_and_ipv6(address):
    with pytest.raises(PublicError):
        validate_url("https://example.com", resolver=resolver([address]))


@pytest.mark.unit
def test_url_policy_rejects_mixed_public_and_private_answers():
    with pytest.raises(PublicError):
        validate_url(
            "https://example.com", resolver=resolver(["93.184.216.34", "127.0.0.1"])
        )


@pytest.mark.unit
def test_redirect_is_revalidated_before_private_target_is_requested():
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(PublicError) as caught:
            bounded_get(client, "https://example.com", resolver=resolver(["93.184.216.34"]))
    assert caught.value.code == "url_not_allowed"
    assert requested == ["https://example.com/"]


@pytest.mark.unit
def test_bounded_fetch_rejects_oversized_or_wrong_media_without_success():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/octet-stream"}, content=b"x")

    limits = FetchLimits(decompressed_bytes=4)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(PublicError) as caught:
            bounded_get(client, "https://example.com", limits=limits, resolver=resolver(["93.184.216.34"]))
    assert caught.value.code == "resource_limit"


@pytest.mark.unit
def test_bounded_fetch_stops_stream_and_closes_on_body_limit():
    state = {"closed": False, "chunks": 0}

    class TrackedStream(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(5):
                state["chunks"] += 1
                yield b"abcd"

        def close(self):
            state["closed"] = True

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, stream=TrackedStream())

    limits = FetchLimits(decompressed_bytes=5)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(PublicError):
            bounded_get(
                client,
                "https://example.com",
                limits=limits,
                resolver=resolver(["93.184.216.34"]),
            )
    assert state == {"closed": True, "chunks": 2}
