"""
Exporter - 知识抽取主流程
支持 Legacy 和 Enhanced adapter 模式
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from registry import get_registry, get_registry_mode
from writers.artifacts_writer import ArtifactsWriter


def _load_parsed(path: Path) -> dict:
    """加载 parsed.json 文件"""
    return json.loads(path.read_text(encoding="utf-8"))


def _select_types(auto: bool, targets: list, text: str) -> list:
    """自动选择要处理的类型"""
    if not auto:
        return targets
    signals = {
        "dfd": sum(text.count(k) for k in ["数据流", "处理", "流程", "外部实体", "数据存储", "data flow", "process", "DFD"]),
        "concepts": sum(text.count(k) for k in ["概念", "定义", "是指", "表示", "definition", "concept"]),
        "rules": sum(text.count(k) for k in ["规则", "必须", "应该", "限制", "约束", "rule"]),
    }
    ordered = sorted(signals.items(), key=lambda x: x[1], reverse=True)
    result = [k for k, v in ordered if v > 0]
    return result or ["concepts", "rules"]


def run(input_glob: str, targets_csv: str, auto: bool, min_score: float) -> dict:
    """
    运行知识抽取流程
    
    Args:
        input_glob: 输入文件的 glob 模式
        targets_csv: 目标类型，逗号分隔
        auto: 是否自动选择类型
        min_score: 最低分数阈值
    
    Returns:
        处理结果摘要
    """
    files = list(Path().glob(input_glob))
    reg = get_registry()
    mode = get_registry_mode()
    writer = ArtifactsWriter()
    saved = []
    
    print(f"[Exporter] Mode: {mode}, Files: {len(files)}")
    
    for f in files:
        parsed = _load_parsed(f)
        if not isinstance(parsed, dict):
            continue
        
        text = parsed.get("clean_text") or parsed.get("markdown") or ""
        url = parsed.get("source_url") or parsed.get("url") or ""
        title = parsed.get("title") or "未命名"
        
        # 解析域名
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
            
            # 构建上下文 - 增强版需要完整的 parsed_data
            ctx = {
                "url": url,
                "title": title,
                "_parsed_data": parsed,  # 传递完整数据给增强版 adapter
            }
            
            # 调用 adapter 构建候选
            cands, trace, metrics, score = builder().build_candidates(text, ctx)
            
            artifact = None
            errors = []
            ok = False
            
            if llm and cands:
                # 调用 LLM 进行结构化抽取
                artifact, llm_trace = llm(cands, {"url": url, "title": title})
                trace = {**(trace or {}), "llm": llm_trace}
                
                if artifact:
                    artifact = normalizer(artifact, namer)
                    ok, errors = validator(artifact, cfg["schema_path"])
            
            # 计算最终得分
            final_score = score
            if artifact:
                try:
                    if t == "dfd":
                        pc = len(artifact.get("processes", []) or [])
                        dfc = len(artifact.get("data_flows", []) or [])
                        dsc = len(artifact.get("data_stores", []) or [])
                        eec = len(artifact.get("external_entities", []) or [])
                        # 增强评分：有多种元素时给更高分
                        element_score = min(1.0, (
                            (pc > 0) * 0.3 + 
                            (dfc > 0) * 0.3 + 
                            (dsc > 0) * 0.2 + 
                            (eec > 0) * 0.2 +
                            min(pc, 5) * 0.05 +
                            min(dfc, 5) * 0.05
                        ))
                        final_score = max(final_score, element_score)
                    elif t == "concepts":
                        cc = len(((artifact.get("generation_knowledge") or {}).get("concepts") or []))
                        final_score = max(final_score, min(1.0, cc / 5.0))
                    elif t == "rules":
                        rc = len(((artifact.get("generation_knowledge") or {}).get("rules") or []))
                        final_score = max(final_score, min(1.0, rc / 6.0))
                except Exception:
                    pass
            
            # 记录 adapter 模式
            trace["adapter_mode"] = cfg.get("mode", "unknown")
            metrics["adapter_mode"] = cfg.get("mode", "unknown")
            
            # 根据验证结果和分数决定输出
            if not ok or final_score < min_score:
                meta = {
                    "source_url": url,
                    "title": title,
                    "type": t,
                    "created_at": datetime.now().isoformat(),
                    "reliability_score": max(0.0, min(final_score, 1.0)),
                    "validated": False,
                    "errors": errors,
                    "adapter_mode": cfg.get("mode", "unknown"),
                }
                out = writer.write(domain, title, parsed, text, t, None, trace, meta, metrics, errors)
                saved.append(out)
                print(f"  [{t}] ❌ score={final_score:.2f} errors={len(errors)}")
                continue
            
            # 验证通过，写入 artifact
            meta = {
                "source_url": url,
                "title": title,
                "type": t,
                "created_at": datetime.now().isoformat(),
                "reliability_score": max(0.0, min(final_score, 1.0)),
                "validated": True,
                "errors": [],
                "adapter_mode": cfg.get("mode", "unknown"),
            }
            out = writer.write(domain, title, parsed, text, t, artifact, trace, meta, metrics, [])
            saved.append(out)
            print(f"  [{t}] ✅ score={final_score:.2f}")
    
    return {"count": len(saved), "outputs": saved[:5], "mode": mode}


def main():
    """命令行入口"""
    p = argparse.ArgumentParser(description="知识抽取导出器")
    p.add_argument("--input-glob", default="data/parsed/*.json",
                   help="输入文件的 glob 模式")
    p.add_argument("--target", default="dfd,concepts,rules",
                   help="目标类型，逗号分隔")
    p.add_argument("--auto", action="store_true",
                   help="自动选择类型")
    p.add_argument("--min-score", type=float, default=0.5,
                   help="最低分数阈值")
    args = p.parse_args()
    
    res = run(args.input_glob, args.target, args.auto, args.min_score)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
