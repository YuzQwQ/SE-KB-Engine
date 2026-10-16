from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from se_kb_app.composition import ApplicationBuilder
from se_kb_app.domain import RetrievalResult
from se_kb_app.settings import AppSettings


class FakeRetrievalService:
    def retrieve(self, request):
        return RetrievalResult(
            request.query,
            request.intent or "concept",
            ({"content": "shared", "score": 0.9, "source": "fixture"},),
        )


@pytest.mark.contract
def test_rest_web_mcp_and_cli_use_the_same_injected_retrieval_service(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.setenv("SKIP_SERVICE_INITIALIZATION", "1")
    settings = AppSettings.from_sources(environ={}, overrides={"project_root": tmp_path})
    application = ApplicationBuilder(settings).with_service("retrieval", FakeRetrievalService()).build()

    from api.app import create_app

    monkeypatch.setenv("KB_READ_KEYS", "read-key")
    flask_app = create_app(application=application, initialize_services=False)
    flask_app.config.update(TESTING=True)
    response = flask_app.test_client().post(
        "/api/v1/search",
        headers={"Authorization": "Bearer read-key"},
        json={"query": "boundary", "intent": "concept", "top_k": 2},
    )
    assert response.status_code == 200
    rest_payload = response.get_json()["data"]

    import server

    monkeypatch.setattr(server, "application", application)
    mcp_payload = json.loads(server.search_knowledge("boundary", "concept", 2, False))
    assert mcp_payload["query"] == rest_payload["query"]
    assert mcp_payload["results"] == rest_payload["results"]

    from web.app import app as web_app, bind_application

    bind_application(application)
    web_app.config.update(TESTING=True)
    web_response = web_app.test_client().post(
        "/api/semantic-search",
        headers={"Authorization": "Bearer read-key"},
        json={"query": "boundary", "intent": "concept", "top_k": 2},
    )
    assert web_response.status_code == 200
    assert web_response.get_json()["results"] == rest_payload["results"]

    from scripts import query_knowledge

    monkeypatch.setattr(sys, "argv", ["query_knowledge.py", "boundary", "--type", "concept", "--json"])
    query_knowledge.main(application)
    assert '"content": "shared"' in capsys.readouterr().out
