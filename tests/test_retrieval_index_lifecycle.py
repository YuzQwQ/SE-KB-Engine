from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from se_kb_app.retrieval.indexing import (
    BuildMode,
    IndexCompatibilityError,
    IndexManager,
    IndexManifest,
)
from se_kb_app.retrieval.models import EvaluationDataset

FIXTURE = Path(__file__).parent / "fixtures" / "retrieval"


def documents():
    return EvaluationDataset.load(FIXTURE / "documents.jsonl", FIXTURE / "queries.jsonl").documents


def manifest(index_id: str) -> IndexManifest:
    return IndexManifest(
        index_id=index_id,
        source_manifest="dataset-1.0.0",
        chunker_version="document-v1",
        embedding_model="hash-vector-v1",
        embedding_dimension=256,
        normalization="l2",
        distance_metric="cosine",
        collection_mapping={"concept": "concepts", "rule": "rules"},
    )


@pytest.mark.unit
def test_index_manifest_rejects_dimension_model_and_schema_mismatch():
    current = manifest("one")
    for changed in (
        replace(current, embedding_dimension=128),
        replace(current, embedding_model="other"),
        replace(current, schema_version="2.0"),
    ):
        with pytest.raises(IndexCompatibilityError, match="rebuild into a new target"):
            current.ensure_compatible(changed)


@pytest.mark.integration
def test_build_modes_stale_cleanup_and_atomic_switch(tmp_path: Path):
    manager = IndexManager(tmp_path / "indexes")
    source = documents()
    dry = manager.build(manifest("one"), source, mode=BuildMode.DRY_RUN)
    assert dry.planned_records == len(source)
    assert not Path(dry.target).exists()

    full = manager.build(manifest("one"), source, mode=BuildMode.FULL, switch=True)
    assert full.valid and full.switched
    assert manager.active_index_id() == "one"
    assert set(manager.load_active()) == {item.id for item in source}

    reduced = source[:-2]
    incremental = manager.build(
        manifest("two"), reduced, mode=BuildMode.INCREMENTAL, switch=True
    )
    assert incremental.stale_removed == tuple(sorted(item.id for item in source[-2:]))
    assert set(manager.load_active()) == {item.id for item in reduced}
    validated = manager.build(
        manifest("two"), (), mode=BuildMode.VALIDATE_ONLY
    )
    assert validated.valid is True


@pytest.mark.integration
def test_failed_build_preserves_prior_index_and_marks_partial_invalid(tmp_path: Path):
    manager = IndexManager(tmp_path / "indexes")
    source = documents()
    manager.build(manifest("stable"), source, mode=BuildMode.FULL, switch=True)
    before = manager.load_active()
    with pytest.raises(OSError, match="injected"):
        manager.build(
            manifest("partial"), source, mode=BuildMode.FULL, switch=True, fail_after_records=2
        )
    assert manager.active_index_id() == "stable"
    assert manager.load_active() == before
    assert (tmp_path / "indexes" / "partial" / "INVALID").is_file()


@pytest.mark.integration
def test_concurrent_readers_observe_only_whole_old_or_new_index(tmp_path: Path):
    manager = IndexManager(tmp_path / "indexes")
    source = documents()
    manager.build(manifest("old"), source, mode=BuildMode.FULL, switch=True)
    old_ids = frozenset(item.id for item in source)
    new_source = source[:4]
    new_ids = frozenset(item.id for item in new_source)

    def read_ids() -> frozenset[str]:
        return frozenset(manager.load_active())

    with ThreadPoolExecutor(max_workers=6) as executor:
        before = [executor.submit(read_ids) for _ in range(10)]
        manager.build(manifest("new"), new_source, mode=BuildMode.FULL, switch=True)
        after = [executor.submit(read_ids) for _ in range(10)]
    observed = {future.result() for future in [*before, *after]}
    assert observed.issubset({old_ids, new_ids})
    assert manager.load_active().keys() == {item.id for item in new_source}
