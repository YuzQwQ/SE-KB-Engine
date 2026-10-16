from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from se_kb_app.retrieval.experiments import PromotionBudgets, evaluate_promotion


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare retrieval benchmark reports against gates")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    budgets = PromotionBudgets(max_ndcg_regression=0.01)
    passed, failures = evaluate_promotion(baseline["metrics"], candidate["metrics"], budgets)
    common = sorted(set(baseline["metrics"]).intersection(candidate["metrics"]))
    result = {
        "baseline": baseline["candidate"],
        "candidate": candidate["candidate"],
        "dataset": candidate["fingerprints"]["dataset"],
        "dataset_version": candidate["fingerprints"]["dataset_version"],
        "budgets": budgets.__dict__,
        "deltas": {
            metric: candidate["metrics"][metric] - baseline["metrics"][metric]
            for metric in common
        },
        "passed": passed,
        "failures": list(failures),
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
