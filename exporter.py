import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from registry import get_registry
from writers.artifacts_writer import ArtifactsWriter

def _load_parsed(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _select_types(auto: bool, targets: list, text: str) -> list:
    if not auto:
        return targets
    signals = {
        "dfd": sum(text.count(k) for k in ["数据流","处理","流程","外部实体","数据存储","data flow","process"]),
        "concepts": sum(text.count(k) for k in ["概念","定义","是指","表示","definition","concept"]),
        "rules": sum(text.count(k) for k in ["规则","必须","应该","限制","约束","rule"]),
    }
    ordered = sorted(signals.items(), key=lambda x: x[1], reverse=True)
    result = [k for k,v in ordered if v>0]
    return result or ["concepts","rules"]

def run(input_glob: str, targets_csv: str, auto: bool, min_score: float) -> dict:
    files = list(Path().glob(input_glob))
    reg = get_registry()
    writer = ArtifactsWriter()
    saved = []
    for f in files:
        parsed = _load_parsed(f)
        if not isinstance(parsed, dict):
            continue
        text = parsed.get("clean_text") or parsed.get("markdown") or ""
        url = parsed.get("source_url") or parsed.get("url") or ""
        title = parsed.get("title") or "未命名"
        domain = ""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc or "unknown"
        except Exception:
            domain = "unknown"
        types = _select_types(auto, [t.strip() for t in targets_csv.split(",") if t.strip()], text)
        for t in types:
            if t not in reg:
                continue
            cfg = reg[t]
            builder = cfg["builder"]
            validator = cfg["validator"]
            normalizer = cfg["normalizer"]
            namer = cfg["namer"]
            llm = cfg.get("llm_extractor")
            cands, trace, metrics, score = builder().build_candidates(text, {"url": url, "title": title})
            artifact = None
            errors = []
            ok = False
            if llm and cands:
                artifact, llm_trace = llm(cands, {"url": url, "title": title})
                trace = {**(trace or {}), "llm": llm_trace}
                artifact = normalizer(artifact, namer)
                ok, errors = validator(artifact, cfg["schema_path"])
            final_score = score
            if artifact:
                try:
                    if t == "dfd":
                        pc = len(artifact.get("processes", []) or [])
                        dfc = len(artifact.get("data_flows", []) or [])
                        final_score = max(final_score, min(1.0, (pc>0) * 0.5 + (dfc>0) * 0.5))
                    elif t == "concepts":
                        cc = len(((artifact.get("generation_knowledge") or {}).get("concepts") or []))
                        final_score = max(final_score, min(1.0, cc/5.0))
                    elif t == "rules":
                        rc = len(((artifact.get("generation_knowledge") or {}).get("rules") or []))
                        final_score = max(final_score, min(1.0, rc/6.0))
                except Exception:
                    pass
            if not ok or final_score < min_score:
                meta = {
                    "source_url": url,
                    "title": title,
                    "type": t,
                    "created_at": datetime.now().isoformat(),
                    "reliability_score": max(0.0, min(final_score, 1.0)),
                    "validated": False,
                    "errors": errors,
                }
                out = writer.write(domain, title, parsed, text, t, None, trace, meta, metrics, errors)
                saved.append(out)
                continue
            meta = {
                "source_url": url,
                "title": title,
                "type": t,
                "created_at": datetime.now().isoformat(),
                "reliability_score": max(0.0, min(final_score, 1.0)),
                "validated": True,
                "errors": [],
            }
            out = writer.write(domain, title, parsed, text, t, artifact, trace, meta, metrics, [])
            saved.append(out)
    return {"count": len(saved), "outputs": saved[:5]}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-glob", default="export/crawler_core/data/parsed/*.json")
    p.add_argument("--target", default="dfd,concepts,rules")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--min-score", type=float, default=0.5)
    args = p.parse_args()
    res = run(args.input_glob, args.target, args.auto, args.min_score)
    print(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()