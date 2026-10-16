from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from se_kb_app.artifacts.identity import artifact_id, content_id, document_id
from se_kb_app.artifacts.models import (
    ArtifactManifest,
    ExtractionOutcome,
    OutcomeTag,
    ProcessingTrace,
    SourceAnchor,
)
from se_kb_app.artifacts.storage import ArtifactPublisher, atomic_write_bytes, derived_file, safe_component


def manifest_for(payload: bytes, *, batch_id: str = "batch-stable") -> ArtifactManifest:
    content_hash = content_id("source")
    doc_id = document_id("https://example.com/article", content_hash)
    art_id = artifact_id(doc_id, "concept", {"name": "boundary", "items": [2, 1]})
    return ArtifactManifest(
        batch_id=batch_id,
        document_id=doc_id,
        source_url="https://example.com/article",
        content_hash=content_hash,
        created_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        trace=ProcessingTrace("0.1.0", "cleaner-v1", "router-v1", "prompt-v1", "model-v1", "params-v1", "concept-v1"),
        outcome=ExtractionOutcome(OutcomeTag.SUCCESS, (art_id,)),
        derived_files=(derived_file("artifacts/concept.json", payload),),
        anchors=(SourceAnchor(doc_id, 10, 20, content_id("support"), ("Heading",)),),
    )


@pytest.mark.unit
def test_stable_ids_ignore_display_filenames_and_mapping_order():
    content_hash = content_id("same content")
    first_doc = document_id("https://example.com/a", content_hash)
    second_doc = document_id("https://example.com/a", content_hash)
    assert first_doc == second_doc
    first = artifact_id(first_doc, "concept", {"b": 2, "a": [1, 2]})
    second = artifact_id(second_doc, "concept", {"a": [1, 2], "b": 2})
    assert first == second
    assert artifact_id(first_doc, "concept", {"a": [2, 1], "b": 2}) != first


@pytest.mark.unit
def test_path_sanitization_is_bounded_and_atomic_failure_preserves_prior_file(tmp_path: Path):
    assert safe_component(" ../unsafe title <> ", maximum=12) == "unsafe-title"
    destination = tmp_path / "value.bin"
    destination.write_bytes(b"prior")

    def fail_replace(source: str, target: str) -> None:
        raise OSError("injected replace failure")

    with pytest.raises(OSError):
        atomic_write_bytes(destination, b"new", replace=fail_replace)
    assert destination.read_bytes() == b"prior"
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.integration
def test_manifest_is_committed_last_and_interruption_is_not_success(tmp_path: Path):
    payload = json.dumps({"name": "boundary"}).encode()
    manifest = manifest_for(payload)
    publisher = ArtifactPublisher(tmp_path)
    with pytest.raises(OSError):
        publisher.publish(
            manifest,
            {"artifacts/concept.json": payload},
            failure_after_files=1,
        )
    batch = tmp_path / "batch-stable"
    assert (batch / "artifacts" / "concept.json").is_file()
    assert not (batch / "manifest.json").exists()

    manifest_path = publisher.publish(manifest, {"artifacts/concept.json": payload})
    loaded = ArtifactManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
    assert loaded == manifest


@pytest.mark.unit
def test_tagged_outcomes_never_promote_failed_artifacts():
    with pytest.raises(ValueError):
        ExtractionOutcome(OutcomeTag.VALIDATION_FAILED, ("art-invalid",))
    with pytest.raises(ValueError):
        ExtractionOutcome(OutcomeTag.SUCCESS)


@pytest.mark.integration
def test_repeat_publication_is_idempotent_and_keeps_provenance(tmp_path: Path):
    payload = b'{"name":"repeat"}'
    manifest = manifest_for(payload, batch_id="repeat")
    publisher = ArtifactPublisher(tmp_path)
    first = publisher.publish(manifest, {"artifacts/concept.json": payload})
    first_bytes = first.read_bytes()
    second = publisher.publish(manifest, {"artifacts/concept.json": payload})
    assert second == first
    assert second.read_bytes() == first_bytes
    assert len(list((tmp_path / "repeat").rglob("manifest.json"))) == 1
