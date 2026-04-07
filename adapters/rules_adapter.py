from typing import Tuple, Dict, Any, List
import re


class RulesAdapter:
    def build_candidates(
        self, text: str, ctx: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], float]:
        sents = [s.strip() for s in re.split(r"[。.!?\n]", text or "") if len(s.strip()) > 10]
        cands = []
        for s in sents:
            if any(
                k in s for k in ["规则", "必须", "应该", "限制", "约束", "如果", "当", "则", "rule"]
            ):
                cands.append({"text": s, "type": "rule"})
        score = min(1.0, len(cands) / 6.0)
        trace = {"count": len(cands), "score": score}
        metrics = {"rule_candidates": len(cands)}
        return cands, trace, metrics, score
