from __future__ import annotations

import json
import sys
import time
import tracemalloc
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.html_cleaner import clean_and_structure


def measure() -> dict[str, Any]:
    corpus = json.loads((PROJECT_ROOT / "tests/fixtures/extraction/technical_corpus.json").read_text(encoding="utf-8"))
    cases = corpus["cases"]
    predicted_count = expected_count = matched_count = noise = sections = metadata = 0
    code_expected = code_retained = rows_expected = rows_retained = headings_expected = headings_retained = 0
    links_expected = links_retained = duplicate_blocks = 0
    tracemalloc.start()
    started = time.perf_counter()
    for case in cases:
        url = f"https://fixture.invalid/{case['id']}"
        document = clean_and_structure(case["html"], url)
        predicted = Counter((block["kind"], block["text"]) for block in document["blocks"] if block["text"])
        expected = Counter((block["kind"], block["text"]) for block in case["expected_blocks"])
        predicted_count += sum(predicted.values())
        expected_count += sum(expected.values())
        matched_count += sum((predicted & expected).values())
        duplicate_blocks += sum(max(0, count - expected.get(key, 1)) for key, count in predicted.items())
        noise += sum(document["clean_text"].lower().count(token) for token in
                     ("cookie banner", "subscribe now", "navigation menu", "advertisement noise"))
        sections += len(document["sections"])
        metadata += sum((document["title"] == case["title"], document["source_url"] == url,
                         bool(document.get("cleaner_version")), bool(document.get("blocks"))))
        code_expected += len(case["expected_code"])
        code_retained += sum(any(block["kind"] == "code" and block["text"] == code for block in document["blocks"])
                             for code in case["expected_code"])
        rows_expected += len(case["expected_table_rows"])
        rows = [row for block in document["blocks"] if block["kind"] == "table" for row in block["rows"]]
        rows_retained += sum(row in rows for row in case["expected_table_rows"])
        headings_expected += len(case["expected_heading_levels"])
        actual_levels = [block["level"] for block in document["blocks"] if block["kind"] == "heading"]
        headings_retained += sum(level in actual_levels for level in case["expected_heading_levels"])
        links_expected += len(case["expected_links"])
        actual_links = {link["url"] for link in document.get("links", [])}
        links_retained += sum(link in actual_links for link in case["expected_links"])
    elapsed = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    precision = matched_count / max(1, predicted_count)
    recall = matched_count / max(1, expected_count)
    return {"cleaner_version": "technical-blocks-v2", "corpus_kind": "synthetic-authored-gold",
            "cases": len(cases), "body_precision": round(precision, 4), "body_recall": round(recall, 4),
            "body_retention_ratio": round(recall, 4), "body_retention_ratio_semantics": "compatibility alias for gold block recall",
            "navigation_noise_hits": noise, "duplicate_blocks": duplicate_blocks,
            "metadata_identity_completeness": metadata / max(1, 4 * len(cases)),
            "code_retention": code_retained / max(1, code_expected),
            "table_row_retention": rows_retained / max(1, rows_expected),
            "heading_retention": headings_retained / max(1, headings_expected),
            "link_retention": links_retained / max(1, links_expected), "sections": sections,
            "runtime_ms": round(elapsed * 1000, 2), "peak_python_memory_bytes": peak,
            "rss_measured": False}


def main() -> int:
    print(json.dumps(measure(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
