from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_delivery import checks
from scripts.check_docs import broken_links
from scripts.exercise_release_rollback import exercise
from scripts.generate_sbom import generate
from scripts.inventory_observability import inventory

ROOT = Path(__file__).parent.parent


@pytest.mark.unit
def test_ci_container_gateway_and_secret_injection_contracts_are_hardened():
    assert checks(ROOT) == []
    compose = (ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "../.env:/app/.env" not in compose
    assert all(path in compose for path in ("/app/data", "/app/cache", "/app/output", "/app/logs", "/app/se_kb"))
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "ubuntu-latest" in ci and "windows-latest" in ci
    assert all(version in ci for version in ('"3.11"', '"3.12"', '"3.13"'))
    assert "coverage.json" in ci and "retention-days: 14" in ci


@pytest.mark.integration
def test_release_upgrade_and_rollback_uses_temporary_byte_identical_copies():
    report = exercise()
    assert report["temporary_root"] is True
    assert report["source_byte_identical"] is True
    assert report["upgrade_ok"] is True
    assert report["rollback_ok"] is True


@pytest.mark.unit
def test_offline_sbom_is_lock_derived_and_deterministic():
    first = generate(ROOT / "uv.lock")
    second = generate(ROOT / "uv.lock")
    assert first == second
    assert first["bomFormat"] == "CycloneDX"
    assert len(first["components"]) > 50


@pytest.mark.unit
def test_documentation_links_and_observability_inventory_are_reviewable():
    assert broken_links(ROOT) == []
    report = inventory(ROOT)
    assert report["counts"]["basic_config"] == 0
    assert set(report["categories"]) == {
        "basic_config", "print", "logger", "sensitive_payload", "health_signal", "metric_source"
    }


@pytest.mark.security
def test_admin_diagnostics_are_authorized_and_do_not_expose_secret(api_client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-do-not-expose-this")
    denied = api_client.get("/api/v1/admin/diagnostics")
    assert denied.status_code == 401
    allowed = api_client.get(
        "/api/v1/admin/diagnostics",
        headers={"Authorization": "Bearer test-admin-key"},
    )
    assert allowed.status_code == 200
    payload = json.dumps(allowed.get_json())
    assert "sk-do-not-expose-this" not in payload
    assert allowed.get_json()["data"]["live"] is True
