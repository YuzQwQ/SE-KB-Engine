from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import tracemalloc
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from se_kb_app.observability import StructuredFormatter


def benchmark(iterations: int = 5000) -> dict[str, object]:
    formatter = StructuredFormatter()
    records = [
        logging.LogRecord(
            "se-kb.benchmark",
            logging.INFO,
            __file__,
            1,
            "stage completed",
            (),
            None,
        )
        for _ in range(iterations)
    ]
    tracemalloc.start()
    started = time.perf_counter()
    lengths = [len(formatter.format(record).encode("utf-8")) for record in records]
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    per_event_ms = elapsed * 1000 / iterations
    maximum_payload = max(lengths, default=0)
    budgets = {"max_per_event_ms": 0.5, "max_payload_bytes": 4096, "max_peak_bytes": 16 * 1024 * 1024}
    passed = (
        per_event_ms <= budgets["max_per_event_ms"]
        and maximum_payload <= budgets["max_payload_bytes"]
        and peak <= budgets["max_peak_bytes"]
    )
    return {
        "iterations": iterations,
        "per_event_ms": per_event_ms,
        "max_payload_bytes": maximum_payload,
        "peak_memory_bytes": peak,
        "budgets": budgets,
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark bounded structured telemetry overhead")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--iterations", type=int, default=5000)
    args = parser.parse_args()
    report = benchmark(args.iterations)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
