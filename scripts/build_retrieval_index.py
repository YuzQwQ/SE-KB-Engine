from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from se_kb_app.retrieval.indexing import BuildMode, IndexManager, IndexManifest
from se_kb_app.retrieval.models import EvaluationDataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an isolated, versioned retrieval index")
    parser.add_argument("index_root", type=Path)
    parser.add_argument("index_id")
    parser.add_argument("--documents", type=Path, default=Path("tests/fixtures/retrieval/documents.jsonl"))
    parser.add_argument("--queries", type=Path, default=Path("tests/fixtures/retrieval/queries.jsonl"))
    parser.add_argument("--mode", choices=tuple(item.value for item in BuildMode), default=BuildMode.DRY_RUN.value)
    parser.add_argument("--switch", action="store_true", help="Atomically activate only after validation")
    args = parser.parse_args()
    if args.switch and args.mode not in {BuildMode.FULL.value, BuildMode.INCREMENTAL.value}:
        parser.error("--switch requires full or incremental mode")
    dataset = EvaluationDataset.load(args.documents, args.queries)
    manifest = IndexManifest(
        index_id=args.index_id,
        source_manifest=f"retrieval-dataset:{dataset.version}:{dataset.fingerprint}",
        chunker_version="document-v1",
        embedding_model="hash-vector-v1",
        embedding_dimension=256,
        normalization="l2",
        distance_metric="cosine",
        collection_mapping={kind: f"fixture-{kind}" for kind in sorted({item.kind for item in dataset.documents})},
    )
    report = IndexManager(args.index_root).build(
        manifest, dataset.documents, mode=BuildMode(args.mode), switch=args.switch
    )
    print(json.dumps(report.__dict__, ensure_ascii=False, indent=2, default=str))
    return 0 if report.valid is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
