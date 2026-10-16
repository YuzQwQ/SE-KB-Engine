from __future__ import annotations

import json
from pathlib import Path

import pytest

from se_kb_app.composition import ApplicationBuilder
from se_kb_app.errors import ApplicationError
from se_kb_app.jobs.models import JobStatus
from se_kb_app.obsidian.jobs import ObsidianJobManager
from se_kb_app.obsidian.models import RelationshipEdge, RelationshipKind
from se_kb_app.obsidian.service import ObsidianVaultService
from se_kb_app.obsidian.source import KnowledgeSelection
from se_kb_app.settings import AppSettings


def _settings(tmp_path: Path, *, enabled: bool) -> AppSettings:
    overrides: dict[str, object] = {"project_root": tmp_path}
    if enabled:
        vault = tmp_path / "vault"
        vault.mkdir(exist_ok=True)
        overrides["obsidian_vault_root"] = vault
        overrides["obsidian_vault_name"] = "Test Vault"
    return AppSettings.from_sources(environ={}, overrides=overrides)


def _artifact(root: Path) -> None:
    batch = root / "se_kb" / "artifacts" / "batch"
    batch.mkdir(parents=True)
    (batch / "metadata.json").write_text(
        json.dumps({"title": "Source", "source_url": "https://example.com/source"}),
        encoding="utf-8",
    )
    (batch / "document.md").write_text("Knowledge body", encoding="utf-8")
    (batch / "dfd_concepts_example.json").write_text(
        json.dumps(
            {
                "concepts": [
                    {"concept_id": "concept_a", "name": "A", "definition": "Alpha"},
                    {"concept_id": "concept_b", "name": "B", "definition": "Beta"},
                ]
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.unit
def test_disabled_service_reports_not_configured_without_initializing_composition(tmp_path: Path):
    settings = _settings(tmp_path, enabled=False)
    application = ApplicationBuilder(settings).with_default_services().build()
    assert "obsidian" not in application.readiness
    with pytest.raises(KeyError):
        application.resource("obsidian")
    service = ObsidianVaultService(settings)
    assert service.status().availability.value == "not_configured"
    with pytest.raises(ApplicationError) as caught:
        service.preview(KnowledgeSelection())
    assert caught.value.public_code == "obsidian_not_configured"


@pytest.mark.integration
def test_service_previews_exports_reports_status_relationships_and_location(tmp_path: Path):
    _artifact(tmp_path)
    settings = _settings(tmp_path, enabled=True)

    def semantic(read):
        return (
            RelationshipEdge(
                "concept_a",
                "concept_b",
                "similar_to",
                RelationshipKind.SEMANTIC,
                score=0.9,
                method="fixture",
            ),
        )

    service = ObsidianVaultService(settings, semantic_provider=semantic)
    preview = service.preview(KnowledgeSelection(), limit=2)
    assert preview.total_actions == 3
    assert preview.partial is True
    assert preview.counts == {"create": 3}

    progress = []
    result = service.export(
        KnowledgeSelection(),
        progress=lambda completed, total, message: progress.append((completed, total, message)),
    )
    assert result.counts == {"create": 3}
    assert progress[0][0] == 10 and progress[-1][0] == 100
    status = service.status()
    assert status.availability.value == "ready"
    assert status.managed_notes == 3

    page = service.relationships(
        KnowledgeSelection(),
        kind=RelationshipKind.SEMANTIC,
        limit=10,
    )
    assert page.total == 1
    location = service.note_location("concept_a")
    assert location.logical_path.endswith(".md")
    assert location.obsidian_uri.startswith("obsidian://open?")
    assert "Test%20Vault" in location.obsidian_uri


@pytest.mark.integration
def test_managed_obsidian_job_reports_progress_result_and_shutdown(tmp_path: Path):
    _artifact(tmp_path)
    service = ObsidianVaultService(_settings(tmp_path, enabled=True))
    manager = ObsidianJobManager(service)
    identifier = manager.submit(KnowledgeSelection())
    manager.runner._futures[identifier].result(timeout=3)
    state = manager.get_state(identifier)
    assert state["status"] == "completed"
    assert state["progress"] == 100
    assert state["results"][0]["counts"] == {"create": 3}
    manager.close()
    assert manager.store.get(identifier).status is JobStatus.SUCCEEDED


@pytest.mark.integration
def test_configured_composition_registers_lazy_obsidian_service_and_closes_cleanly(tmp_path: Path):
    settings = _settings(tmp_path, enabled=True)
    application = ApplicationBuilder(settings).with_default_services().build()
    assert application.readiness == {}
    service = application.resource("obsidian")
    assert isinstance(service, ObsidianVaultService)
    application.close()
