from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

from service_boundary.flask_support import ConcurrencyLimiter, RequestLimiter, install_flask_boundary


def read_headers(token: str = "test-read-key") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": "contract-request-1"}


@pytest.mark.contract
def test_api_health_success_shape_is_preserved(api_client):
    response = api_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json() == {
        "code": 200,
        "status": "degraded",
        "service": "se-kb-api",
        "version": "1.0.0",
    }
    assert response.headers["X-Correlation-ID"]


@pytest.mark.contract
def test_api_search_success_shape_is_preserved(api_client):
    result = SimpleNamespace(
        text="safe result",
        score=0.125,
        metadata={"source": "fixture", "type": "concept"},
        collection="concepts",
    )
    response_model = SimpleNamespace(
        query="what is dfd",
        intent=SimpleNamespace(value="concept"),
        total_found=1,
        results=[result],
    )
    retriever = SimpleNamespace(retrieve=lambda *_args: response_model)
    with api_client.application.app_context():
        api_client.application.config["RETRIEVER"] = retriever
    response = api_client.post(
        "/api/v1/search", json={"query": "what is dfd", "top_k": 1}, headers=read_headers()
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload) == {"code", "message", "data"}
    assert payload["data"]["results"][0]["content"] == "safe result"


@pytest.mark.contract
def test_web_start_success_shape_is_preserved(web_client, web_admin_headers, monkeypatch):
    import web.app as web_app

    started = []

    from concurrent.futures import Future
    def queue_without_running(function, *args, **kwargs):
        started.append((function, args, kwargs))
        return Future()
    monkeypatch.setattr(web_app.services.task_manager._executor, "submit", queue_without_running)
    monkeypatch.setattr(web_app.services.task_manager, "status", "idle")
    response = web_client.post(
        "/api/start", json={"query": "boundary", "limit": 3}, headers=web_admin_headers
    )
    assert response.status_code == 200
    assert response.get_json() == {"message": "任务已启动"}
    assert len(started) == 1


@pytest.mark.contract
def test_mcp_read_tool_success_shape_is_preserved(isolated_data_root: Path, monkeypatch):
    import server

    monkeypatch.setattr(server.crawler, "get_available_engines", lambda: ["fixture"])
    monkeypatch.setattr(
        server.crawler,
        "get_engine_info",
        lambda _engine: {"api_name": "Fixture", "parameters": {}, "parsing_rules": {}},
    )
    payload = json.loads(server.get_available_search_engines())
    assert "available_engines" in payload
    assert payload["engine_details"]["fixture"]["api_name"] == "Fixture"


@pytest.mark.security
def test_mcp_admin_tool_requires_admin_without_mutating(isolated_data_root: Path, monkeypatch):
    import server

    calls: list[str] = []
    monkeypatch.setenv("KB_READ_KEYS", "test-read-key")
    monkeypatch.setenv("KB_ADMIN_KEYS", "test-admin-key")
    original_loads = server.json.loads
    def tracked_loads(value):
        calls.append("parsed")
        return original_loads(value)

    monkeypatch.setattr(server.json, "loads", tracked_loads)
    config = json.dumps({"engine": "fixture", "parsing_rules": {}})
    with pytest.raises(Exception) as denied:
        server.configure_search_engine(
            "fixture", config, authorization="Bearer test-read-key", correlation_id="mcp-request"
        )
    assert str(denied.value) == "forbidden"
    assert calls == []


@pytest.mark.security
def test_mcp_invalid_top_k_does_not_invoke_retrieval(isolated_data_root: Path, monkeypatch):
    import server

    calls = []
    monkeypatch.setattr(
        server,
        "knowledge_retriever",
        SimpleNamespace(retrieve=lambda *_args: calls.append(_args)),
    )
    with pytest.raises(Exception) as caught:
        server.search_knowledge("query", top_k=-1)
    assert str(caught.value) == "invalid_field"
    assert calls == []


@pytest.mark.security
@pytest.mark.parametrize(
    ("authorization", "status", "code"),
    [
        (None, 401, "unauthorized"),
        ("test-read-key", 401, "unauthorized"),
        ("Basic test-read-key", 401, "unauthorized"),
        ("Bearer invalid", 401, "unauthorized"),
        ("Bearer test-read-key", 403, "forbidden"),
    ],
)
def test_admin_auth_contract(api_client, authorization, status, code):
    headers = {"Authorization": authorization} if authorization else {}
    response = api_client.get("/api/v1/admin/stats", headers=headers)
    assert response.status_code == status
    assert response.get_json()["error"]["code"] == code


@pytest.mark.security
def test_invalid_top_k_does_not_invoke_retrieval(api_client):
    calls = []
    api_client.application.config["RETRIEVER"] = SimpleNamespace(
        retrieve=lambda *_args: calls.append(_args)
    )
    response = api_client.post(
        "/api/v1/search", json={"query": "x", "top_k": -1}, headers=read_headers()
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["field"] == "top_k"
    assert calls == []


@pytest.mark.security
def test_missing_retriever_has_separate_liveness_and_readiness(api_client):
    assert api_client.get("/api/v1/live").status_code == 200
    ready = api_client.get("/api/v1/ready")
    assert ready.status_code == 503
    capabilities = ready.get_json()["capabilities"]
    assert capabilities["retriever"] == "unavailable"
    assert set(capabilities) == {"retriever", "model", "browser", "tor"}
    search = api_client.post("/api/v1/search", json={"query": "x"}, headers=read_headers())
    assert search.status_code == 503
    assert search.get_json()["error"]["code"] == "unavailable"


@pytest.mark.security
def test_cross_origin_or_missing_csrf_cannot_clear_state(web_client, monkeypatch):
    import web.app as web_app

    calls = []
    monkeypatch.setattr(web_app.services.url_index, "clear", lambda: calls.append("cleared"))
    response = web_client.post(
        "/api/url-index/clear",
        headers={"Authorization": "Bearer test-admin-key", "Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "csrf_rejected"
    assert calls == []


@pytest.mark.security
def test_authorized_browser_mutation_changes_state(web_client, web_admin_headers, monkeypatch):
    import web.app as web_app

    calls = []
    monkeypatch.setattr(web_app.services.url_index, "clear", lambda: calls.append("cleared"))
    response = web_client.post("/api/url-index/clear", headers=web_admin_headers)
    assert response.status_code == 200
    assert calls == ["cleared"]


@pytest.mark.security
def test_internal_exception_is_correlated_without_secret_or_path(api_client, caplog):
    secret = "never-return-this-secret"

    class BrokenRetriever:
        def retrieve(self, *_args):
            raise RuntimeError(f"{secret} C:\\private\\database.sqlite")

    api_client.application.config["RETRIEVER"] = BrokenRetriever()
    caplog.set_level(logging.ERROR)
    response = api_client.post(
        "/api/v1/search", json={"query": "x"}, headers=read_headers()
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_error"
    assert secret not in body
    assert "database.sqlite" not in body


@pytest.mark.security
def test_web_script_uses_text_nodes_for_server_controlled_content():
    script = (Path(__file__).parents[1] / "web" / "static" / "script.js").read_text(encoding="utf-8")
    assert "${item.source" not in script
    assert "${item.content" not in script
    assert "div.innerHTML = `<span" not in script
    assert "document.createTextNode" in script


@pytest.mark.security
def test_request_body_limit_returns_public_413(api_client):
    response = api_client.post(
        "/api/v1/search",
        data=b"x" * 1_048_577,
        content_type="application/json",
        headers=read_headers(),
    )
    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "body_too_large"


@pytest.mark.security
def test_rate_and_concurrency_limits_are_deterministic():
    now = [0.0]
    rate = RequestLimiter(2, 60.0, clock=lambda: now[0])
    assert rate.allow("client") is True
    assert rate.allow("client") is True
    assert rate.allow("client") is False
    now[0] = 61.0
    assert rate.allow("client") is True

    concurrency = ConcurrencyLimiter(1)
    assert concurrency.acquire() is True
    assert concurrency.acquire() is False
    concurrency.release()
    assert concurrency.acquire() is True
    concurrency.release()


@pytest.mark.security
def test_cors_allows_only_configured_exact_origin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://console.example")
    app = Flask("cors-test")
    install_flask_boundary(app)

    @app.get("/probe")
    def probe():
        return {"ok": True}

    client = app.test_client()
    allowed = client.get("/probe", headers={"Origin": "https://console.example"})
    denied = client.get("/probe", headers={"Origin": "https://evil.example"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "https://console.example"
    assert "Access-Control-Allow-Origin" not in denied.headers
