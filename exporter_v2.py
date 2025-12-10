"""
Exporter V2 - 基于两阶段抽取架构的知识导出器
Stage 1: Type Router (轻量模型判断类型)
Stage 2: Specialized Extractors (专用模型结构化抽取)
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from extractors.pipeline import ExtractionPipeline, run_pipeline
from extractors.type_registry import get_type_registry
from validators.jsonschema_validator import make_validator
from writers.artifacts_writer import ArtifactsWriter


def _load_env_file():
    """加载 .env 文件"""
    env_path = Path('.env')
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    k, v = k.strip(), v.strip()
                    if k and v and os.getenv(k) is None:
                        os.environ[k] = v
        except Exception:
            pass


# 加载环境变量
_load_env_file()


def _load_parsed(path: Path) -> dict:
    """加载 parsed.json 文件"""
    return json.loads(path.read_text(encoding="utf-8"))


def run(input_glob: str, 
        force_types: List[str] = None, 
        min_score: float = 0.5,
        skip_validation: bool = False) -> dict:
    """
    运行两阶段知识抽取流程
    
    Args:
        input_glob: 输入文件的 glob 模式
        force_types: 强制指定类型（跳过路由）
        min_score: 最低分数阈值（保留兼容性）
        skip_validation: 是否跳过 Schema 校验
    
    Returns:
        处理结果摘要
    """
    files = list(Path().glob(input_glob))
    registry = get_type_registry()
    writer = ArtifactsWriter()
    validator = make_validator()
    
    results = []
    total_tokens = 0
    
    print(f"[Exporter V2] Two-Stage Architecture")
    print(f"[Exporter V2] Files: {len(files)}")
    if force_types:
        print(f"[Exporter V2] Force Types: {force_types}")
    
    for f in files:
        parsed = _load_parsed(f)
        if not isinstance(parsed, dict):
            continue
        
        url = parsed.get("source_url") or parsed.get("url") or ""
        title = parsed.get("title") or "未命名"
        text = parsed.get("clean_text") or parsed.get("markdown") or ""
        
        # 解析域名
        domain = "unknown"
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc or "unknown"
        except Exception:
            pass
        
        print(f"\n📄 Processing: {title[:50]}...")
        
        # 执行两阶段流水线
        pipeline_result = run_pipeline(parsed, force_types)
        total_tokens += pipeline_result.total_tokens
        
        print(f"   🔀 Routed: {pipeline_result.routed_types}")
        
        # 处理每个成功的 artifact
        for type_id, artifact in pipeline_result.artifacts.items():
            kt = registry.get(type_id)
            schema_path = kt.schema_path if kt else None
            
            # Schema 校验
            ok, errors = True, []
            if not skip_validation and schema_path and Path(schema_path).exists():
                ok, errors = validator(artifact, schema_path)
            
            # 计算分数（基于抽取结果的完整度）
            score = _calculate_score(type_id, artifact)
            
            if not ok or score < min_score:
                meta = {
                    "source_url": url,
                    "title": title,
                    "type": type_id,
                    "created_at": datetime.now().isoformat(),
                    "reliability_score": score,
                    "validated": False,
                    "errors": errors,
                    "architecture": "two_stage",
                }
                out = writer.write(
                    domain, title, parsed, text, type_id, 
                    None, pipeline_result.trace, meta, 
                    {"tokens": pipeline_result.total_tokens}, errors
                )
                results.append(out)
                print(f"   [{type_id}] ❌ score={score:.2f} errors={len(errors)}")
                continue
            
            # 写入成功的 artifact
            meta = {
                "source_url": url,
                "title": title,
                "type": type_id,
                "created_at": datetime.now().isoformat(),
                "reliability_score": score,
                "validated": True,
                "errors": [],
                "architecture": "two_stage",
            }
            out = writer.write(
                domain, title, parsed, text, type_id,
                artifact, pipeline_result.trace, meta,
                {"tokens": pipeline_result.total_tokens}, []
            )
            results.append(out)
            print(f"   [{type_id}] ✅ score={score:.2f}")
        
        # 处理错误
        for type_id, error in pipeline_result.errors.items():
            if type_id not in pipeline_result.artifacts:
                print(f"   [{type_id}] ❌ {error}")
    
    return {
        "count": len(results),
        "outputs": results[:10],
        "total_tokens": total_tokens,
        "architecture": "two_stage",
    }


def _calculate_score(type_id: str, artifact: Dict[str, Any]) -> float:
    """根据抽取结果计算分数"""
    if not artifact:
        return 0.0
    
    try:
        if type_id == 'dfd':
            processes = len(artifact.get('processes', []) or [])
            flows = len(artifact.get('data_flows', []) or [])
            stores = len(artifact.get('data_stores', []) or [])
            entities = len(artifact.get('external_entities', []) or [])
            
            # DFD 完整度评分
            score = min(1.0, (
                (processes > 0) * 0.25 +
                (flows > 0) * 0.25 +
                (stores > 0) * 0.15 +
                (entities > 0) * 0.15 +
                min(processes, 5) * 0.04 +
                min(flows, 5) * 0.04
            ))
            return max(score, 0.5 if processes > 0 else 0.2)
        
        elif type_id == 'concepts':
            concepts = (artifact.get('generation_knowledge', {}).get('concepts', []))
            return min(1.0, len(concepts) / 5.0) if concepts else 0.2
        
        elif type_id == 'rules':
            rules = (artifact.get('generation_knowledge', {}).get('rules', []))
            return min(1.0, len(rules) / 4.0) if rules else 0.2
        
        elif type_id == 'patterns':
            patterns = (artifact.get('generation_knowledge', {}).get('patterns', []))
            return min(1.0, len(patterns) / 3.0) if patterns else 0.2
        
        elif type_id == 'transformations':
            trans = (artifact.get('generation_knowledge', {}).get('transformations', []))
            return min(1.0, len(trans) / 2.0) if trans else 0.2
        
        elif type_id == 'validation':
            vk = artifact.get('validation_knowledge', {})
            criteria = len(vk.get('criteria', []))
            checklist = len(vk.get('checklist', []))
            errors = len(vk.get('error_patterns', []))
            total = criteria + checklist + errors
            return min(1.0, total / 5.0) if total > 0 else 0.2
        
        else:
            return 0.5
    
    except Exception:
        return 0.3


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="Exporter V2 - 两阶段知识抽取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自动路由类型
  python exporter_v2.py --input-glob "data/parsed/*.json"
  
  # 强制指定类型（跳过路由）
  python exporter_v2.py --input-glob "data/parsed/*.json" --force-types dfd,concepts
  
  # 单文件测试
  python exporter_v2.py --input-glob "data/parsed/example.json" --force-types dfd
"""
    )
    parser.add_argument(
        "--input-glob", 
        default="data/parsed/*.json",
        help="输入文件的 glob 模式"
    )
    parser.add_argument(
        "--force-types", "-t",
        help="强制指定类型（逗号分隔），跳过路由阶段"
    )
    parser.add_argument(
        "--min-score", 
        type=float, 
        default=0.4,
        help="最低分数阈值"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="跳过 Schema 校验"
    )
    
    args = parser.parse_args()
    
    force_types = args.force_types.split(',') if args.force_types else None
    
    result = run(
        args.input_glob,
        force_types=force_types,
        min_score=args.min_score,
        skip_validation=args.skip_validation
    )
    
    print("\n" + "=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

