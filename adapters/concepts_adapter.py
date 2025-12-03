from typing import Tuple, Dict, Any, List
import re

class ConceptsAdapter:
    def build_candidates(self, text: str, ctx: Dict[str,Any]) -> Tuple[List[Dict[str,Any]], Dict[str,Any], Dict[str,Any], float]:
        sents = [s.strip() for s in re.split(r"[。.!?\n]", text or "") if len(s.strip())>10]
        cands = []
        for s in sents:
            if any(k in s for k in ["概念","定义","是指","表示","definition","concept"]):
                cands.append({"text": s, "type": "concept"})
        score = min(1.0, len(cands)/5.0)
        trace = {"count": len(cands), "score": score}
        metrics = {"concept_candidates": len(cands)}
        return cands, trace, metrics, score