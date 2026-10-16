from __future__ import annotations

import httpx
import pytest

from tests.fixtures.http_server import local_http_fixture


@pytest.mark.integration
def test_local_http_fixture_covers_reliability_cases():
    with local_http_fixture() as (base_url, counts), httpx.Client(follow_redirects=False) as client:
        assert client.get(f"{base_url}/ok").status_code == 200
        redirect = client.get(f"{base_url}/redirect")
        assert redirect.status_code == 302 and redirect.headers["location"] == "/ok"
        assert client.get(f"{base_url}/retry").status_code == 503
        assert client.get(f"{base_url}/retry").status_code == 200
        assert client.get(f"{base_url}/delay?seconds=0.01").text == "delayed"
        compressed = client.get(f"{base_url}/gzip")
        assert compressed.text == "compressed content"
        assert compressed.headers["content-encoding"] == "gzip"
        assert "valid-prefix" in client.get(f"{base_url}/malformed-encoding").text
        assert len(client.get(f"{base_url}/large").content) == 2 * 1024 * 1024
        assert client.get(f"{base_url}/challenge").status_code == 403
        with pytest.raises(httpx.TransportError):
            client.get(f"{base_url}/disconnect")
        assert counts["/retry"] == 2
