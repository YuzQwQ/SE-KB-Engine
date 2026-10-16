from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from se_kb_app.retrieval.indexing import BuildMode, IndexManager, IndexManifest
from se_kb_app.retrieval.models import EvaluationDataset

FIXTURE = PROJECT_ROOT / "tests" / "fixtures"


def snapshot(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def manifest(index_id: str, dataset: EvaluationDataset) -> IndexManifest:
    return IndexManifest(
        index_id=index_id,
        source_manifest=f"dataset:{dataset.fingerprint}",
        chunker_version="document-v1",
        embedding_model="hash-vector-v1",
        embedding_dimension=256,
        normalization="l2",
        distance_metric="cosine",
        collection_mapping={"all": "fixture"},
    )


def exercise() -> dict[str, object]:
    dataset = EvaluationDataset.load(FIXTURE / "retrieval" / "documents.jsonl", FIXTURE / "retrieval" / "queries.jsonl")
    with tempfile.TemporaryDirectory(prefix="se-kb-release-exercise-") as temporary:
        root = Path(temporary)
        artifact_source = root / "artifact-source"
        shutil.copytree(FIXTURE / "artifacts" / "legacy", artifact_source)
        source_before = snapshot(artifact_source)
        manager = IndexManager(root / "indexes")
        manager.build(manifest("release-old", dataset), dataset.documents, mode=BuildMode.FULL, switch=True)
        old_snapshot = manager.load_active()
        manager.build(manifest("release-new", dataset), dataset.documents, mode=BuildMode.FULL, switch=True)
        upgrade_ok = manager.active_index_id() == "release-new"
        manager.switch("release-old", expected=manifest("release-old", dataset))
        rollback_ok = manager.active_index_id() == "release-old" and manager.load_active() == old_snapshot
        return {
            "temporary_root": True,
            "source_byte_identical": snapshot(artifact_source) == source_before,
            "upgrade_ok": upgrade_ok,
            "rollback_ok": rollback_ok,
            "active_after_rollback": manager.active_index_id(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise isolated release index upgrade and rollback")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = exercise()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if all(report[key] for key in ("source_byte_identical", "upgrade_ok", "rollback_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
