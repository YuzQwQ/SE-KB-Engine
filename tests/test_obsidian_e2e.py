from __future__ import annotations

import json
from pathlib import Path

import pytest

from se_kb_app.obsidian.service import ObsidianVaultService
from se_kb_app.obsidian.source import KnowledgeSelection
from se_kb_app.settings import AppSettings


@pytest.mark.integration
def test_multilingual_corpus_exports_incrementally_and_preserves_user_conflict(tmp_path: Path):
    vault = tmp_path / "我的知识库"
    vault.mkdir()
    batch = tmp_path / "se_kb" / "artifacts" / "2026" / "09" / "18" / "批次"
    batch.mkdir(parents=True)
    (batch / "metadata.json").write_text(
        json.dumps(
            {"title": "向量检索 / Vector Retrieval", "source_url": "https://example.com/知识"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (batch / "document.md").write_text("# 混合检索\n\nCombine lexical and vector evidence.", encoding="utf-8")
    (batch / "dfd_concepts_fixture.json").write_text(
        json.dumps(
            {
                "concepts": [
                    {"concept_id": "概念_vector", "name": "向量索引", "definition": "近似语义查找。"},
                    {
                        "concept_id": "concept_hybrid",
                        "name": "Hybrid retrieval",
                        "definition": "Combines multiple signals.",
                        "relationships": [{"target_id": "概念_vector"}],
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    settings = AppSettings.from_sources(
        environ={},
        overrides={
            "project_root": tmp_path,
            "obsidian_vault_root": vault,
            "obsidian_vault_name": "我的知识库",
        },
    )
    service = ObsidianVaultService(settings)
    selection = KnowledgeSelection()

    first_preview = service.preview(selection)
    assert first_preview.counts == {"create": 3}
    first_result = service.export(selection)
    assert first_result.counts == {"create": 3}

    second_preview = service.preview(selection)
    assert second_preview.counts == {"unchanged": 3}
    second_result = service.export(selection)
    assert second_result.counts == {"unchanged": 3}

    target = vault / "SE-KB" / next(
        item.logical_path for item in second_preview.actions if item.identifier == "概念_vector"
    )
    target.write_bytes(target.read_bytes() + "\n人工备注：保留。\n".encode("utf-8"))
    conflict_preview = service.preview(selection)
    conflict = next(item for item in conflict_preview.actions if item.identifier == "概念_vector")
    assert conflict.action.value == "conflict"
    before = target.read_bytes()
    result = service.export(selection)
    assert result.counts["conflict"] == 1
    assert target.read_bytes() == before
    assert "人工备注：保留。" in target.read_text(encoding="utf-8")


@pytest.mark.contract
def test_obsidian_workspace_dom_contract_and_safe_dynamic_rendering():
    root = Path(__file__).parents[1]
    html = (root / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    script = (root / "web" / "static" / "script.js").read_text(encoding="utf-8")
    required_ids = {
        "vaultTab",
        "vault-tab",
        "vaultRefreshBtn",
        "vaultPreviewBtn",
        "vaultExportBtn",
        "vaultPlanBody",
        "vaultGraph",
        "vaultRelationshipBody",
    }
    assert all(f'id="{identifier}"' in html for identifier in required_ids)
    assert 'role="tabpanel" aria-labelledby="vaultTab"' in html
    assert 'role="img" aria-labelledby="knowledgeMapHeading vaultGraphStatus"' in html
    assert "document.createElementNS" in script
    assert "label.textContent" in script
    assert "sourceCell.textContent" in script
    assert "targetCell.textContent" in script
    assert "vaultGraph.innerHTML" not in script
    assert "vaultRelationshipBody.innerHTML" not in script
