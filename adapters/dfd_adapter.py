import json
from pathlib import Path
from typing import Tuple, Dict, Any, List


class DFDAdapter:
    def _signals(self, text: str) -> Dict[str, int]:
        cues = json.loads(Path("se_kb/mappings/semantic_cues.json").read_text(encoding="utf-8"))
        s = {
            "process": sum(text.count(k) for k in cues.get("process", [])),
            "data_flow": sum(text.count(k) for k in cues.get("data_flow", [])),
            "data_store": sum(text.count(k) for k in cues.get("data_store", [])),
            "external_entity": sum(text.count(k) for k in cues.get("external_entity", [])),
        }
        return s

    def build_candidates(
        self, text: str, ctx: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], float]:
        sig = self._signals(text or "")
        score = min(
            1.0,
            (
                sig["process"] * 0.4
                + sig["data_flow"] * 0.3
                + sig["data_store"] * 0.2
                + sig["external_entity"] * 0.1
            )
            / 10.0,
        )
        cands = []
        if sig["process"] + sig["data_flow"] + sig["data_store"] + sig["external_entity"] > 0:
            cands.append({"text": (ctx.get("title") or ""), "type": "dfd"})
        trace = {"signals": sig, "score": score}
        metrics = {"signal_sum": sum(sig.values())}
        return cands, trace, metrics, score
