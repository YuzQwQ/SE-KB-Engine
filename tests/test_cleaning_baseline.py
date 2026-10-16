from __future__ import annotations

import pytest

from scripts.measure_cleaning_baseline import measure


@pytest.mark.integration
def test_cleaning_quality_runtime_and_memory_baseline():
    report = measure()
    assert report["cases"] >= 50
    assert report["body_precision"] >= 0.95
    assert report["body_recall"] >= 0.95
    assert report["duplicate_blocks"] == 0
    for metric in ("code_retention", "table_row_retention", "heading_retention", "link_retention"):
        assert report[metric] == 1.0
    assert report["navigation_noise_hits"] == 0
    assert report["metadata_identity_completeness"] == 1.0
    assert report["sections"] >= 10
    assert report["runtime_ms"] < 5000
    assert report["peak_python_memory_bytes"] < 16 * 1024 * 1024
