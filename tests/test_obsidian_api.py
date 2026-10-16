from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from se_kb_app.obsidian.jobs import ObsidianJobManager
from se_kb_app.obsidian.service import ObsidianVaultService
from se_kb_app.settings import AppSettings


def _runtime(tmp_path: Path) -> ObsidianJobManager:
    vault = tmp_path / "vault"
    vault.mkdir()
    batch = tmp_path / "se_kb" / "artifacts" / "batch"
    batch.mkdir(parents=True)
    (batch / "metadata.json").write_text(
        json.dumps({"title": "API Source", "source_url": "https://example.com/api"}),
        encoding="utf-8",
    )
    (batch / "document.md").write_text("API body", encoding="utf-8")
    (batch / "dfd_concepts_api.json").write_text(
        json.dumps(
            {
                "concepts": [
                    {
                        "concept_id": "api_concept_a",
                        "name": "API A",
                        "definition": "A",
                        "relationships": [{"target_id": "api_concept_b"}],
                    },
                    {"concept_id": "api_concept_b", "name": "API B", "definition": "B"},
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = AppSettings.from_sources(
        environ={},
        overrides={
            "project_root": tmp_path,
            "obsidian_vault_root": vault,
            "obsidian_vault_name": "API Vault",
        },
    )
    return ObsidianJobManager(ObsidianVaultService(settings))


def _read_headers():
    return {"Authorization": "Bearer test-read-key"}


@pytest.mark.security
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/obsidian/status"),
        ("post", "/api/obsidian/preview"),
        ("get", "/api/obsidian/relationships"),
        ("get", "/api/obsidian/notes/anything/location"),
    ],
)
def test_obsidian_read_endpoints_require_authentication(web_client, method, path):
    response = getattr(web_client, method)(path, json={} if method == "post" else None)
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


@pytest.mark.contract
def test_obsidian_status_preview_relationship_and_location_contracts(
    web_client, web_admin_headers, tmp_path: Path, monkeypatch
):
    runtime = _runtime(tmp_path)
    monkeypatch.setitem(web_client.application.config, "OBSIDIAN_RUNTIME", runtime)
    status = web_client.get("/api/obsidian/status", headers=_read_headers())
    assert status.status_code == 200
    assert status.get_json()["availability"] == "ready"
    assert "vault_root" not in status.get_json()

    preview = web_client.post(
        "/api/obsidian/preview",
        json={"minimum_quality": 0, "offset": 0, "limit": 2},
        headers=_read_headers(),
    )
    assert preview.status_code == 200
    assert preview.get_json()["total"] == 3
    assert preview.get_json()["partial"] is True

    export = web_client.post("/api/obsidian/export", json={}, headers=web_admin_headers)
    assert export.status_code == 202
    identifier = export.get_json()["job_id"]
    assert export.headers["Location"] == f"/api/jobs/{identifier}"
    runtime.runner._futures[identifier].result(timeout=3)
    job = web_client.get(f"/api/jobs/{identifier}", headers=_read_headers())
    assert job.status_code == 200
    assert job.get_json()["status"] == "completed"

    relationships = web_client.get(
        "/api/obsidian/relationships?kind=explicit&limit=1",
        headers=_read_headers(),
    )
    assert relationships.status_code == 200
    assert relationships.get_json()["partial"] is True
    assert len(relationships.get_json()["edges"]) == 1

    location = web_client.get(
        "/api/obsidian/notes/api_concept_a/location",
        headers=_read_headers(),
    )
    assert location.status_code == 200
    payload = location.get_json()
    assert payload["logical_path"].endswith(".md")
    assert payload["obsidian_uri"].startswith("obsidian://open?")
    assert str(tmp_path) not in location.get_data(as_text=True)
    runtime.close()


@pytest.mark.security
def test_obsidian_export_requires_admin_csrf_and_validation_is_bounded(web_client, tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path)
    monkeypatch.setitem(web_client.application.config, "OBSIDIAN_RUNTIME", runtime)
    denied = web_client.post(
        "/api/obsidian/export",
        json={},
        headers={"Authorization": "Bearer test-read-key"},
    )
    assert denied.status_code == 403
    assert denied.get_json()["error"]["code"] == "forbidden"

    invalid_preview = web_client.post(
        "/api/obsidian/preview",
        json={"minimum_quality": 2},
        headers=_read_headers(),
    )
    assert invalid_preview.status_code == 400
    assert invalid_preview.get_json()["error"]["field"] == "minimum_quality"
    invalid_page = web_client.get(
        "/api/obsidian/relationships?limit=1001&minimum_score=-1",
        headers=_read_headers(),
    )
    assert invalid_page.status_code == 400
    runtime.close()


@pytest.mark.security
def test_unconfigured_preview_is_redacted_and_does_not_expose_host_path(web_client, tmp_path: Path, monkeypatch):
    settings = AppSettings.from_sources(environ={}, overrides={"project_root": tmp_path})
    runtime = ObsidianJobManager(ObsidianVaultService(settings))
    monkeypatch.setitem(web_client.application.config, "OBSIDIAN_RUNTIME", runtime)
    response = web_client.post("/api/obsidian/preview", json={}, headers=_read_headers())
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "unavailable"
    assert str(tmp_path) not in response.get_data(as_text=True)
    runtime.close()


@pytest.mark.contract
def test_obsidian_export_reuses_shared_job_cancellation_contract(
    web_client, web_admin_headers, monkeypatch
):
    started = threading.Event()
    stopped = threading.Event()

    class BlockingService:
        def export(self, _selection, *, cancellation, progress):
            progress(10, 100, "started")
            started.set()
            try:
                while True:
                    cancellation.checkpoint()
                    stopped.wait(0.005)
            finally:
                stopped.set()

        def close(self):
            return None

    runtime = ObsidianJobManager(BlockingService())
    monkeypatch.setitem(web_client.application.config, "OBSIDIAN_RUNTIME", runtime)
    response = web_client.post("/api/obsidian/export", json={}, headers=web_admin_headers)
    assert response.status_code == 202
    identifier = response.get_json()["job_id"]
    assert started.wait(timeout=1)
    cancelled = web_client.post(f"/api/jobs/{identifier}/cancel", headers=web_admin_headers)
    assert cancelled.status_code == 200
    assert cancelled.get_json()["status"] == "cancelled"
    assert stopped.wait(timeout=1)
    runtime.close()
