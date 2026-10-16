"""
测试两阶段抽取流水线

用法:
    python scripts/test_pipeline.py [parsed_json_path]
    python scripts/test_pipeline.py --force-types dfd,concepts  # 跳过路由
"""

import sys
import json
import argparse
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.pipeline import run_pipeline_from_file
from extractors.type_router import TypeRouter
from extractors.type_registry import get_type_registry


def test_type_registry():
    """测试类型注册表"""
    print("=" * 60)
    print("📋 类型注册表")
    print("=" * 60)
    
    registry = get_type_registry()
    
    print("\n已启用的类型:")
    for kt in registry.get_enabled():
        print(f"  - {kt.type_id}: {kt.name}")
        print(f"    简介: {kt.brief[:60]}...")
    
    print("\n路由用类型描述:")
    print("-" * 40)
    print(registry.get_routing_prompt_section())


def test_router(parsed_path: str):
    """测试类型路由器"""
    print("\n" + "=" * 60)
    print("🔀 Stage 1: Type Router 测试")
    print("=" * 60)
    
    parsed_data = json.loads(Path(parsed_path).read_text(encoding='utf-8'))
    
    print(f"\n📄 标题: {parsed_data.get('title', 'N/A')}")
    print(f"🔗 URL: {parsed_data.get('source_url', 'N/A')}")
    
    router = TypeRouter()
    
    print("\n配置:")
    print(f"  - Model: {router.model_id}")
    print(f"  - Base URL: {router.base_url[:40]}..." if router.base_url else "  - Base URL: 未配置")
    
    if not router.base_url or not router.api_key:
        print("\n⚠️ 未配置 FILTER_BASE_URL 或 FILTER_API_KEY")
        return None
    
    print("\n🔄 正在调用 Router...")
    result, trace = router.route(parsed_data)
    
    print("\n📊 路由结果:")
    print(f"  - 识别类型: {result.types}")
    print(f"  - 置信度: {result.confidences}")
    print(f"  - 推理: {result.reasoning}")
    print(f"  - Tokens: {result.tokens_used}")
    
    return result.types


def test_full_pipeline(parsed_path: str, force_types: list = None):
    """测试完整流水线"""
    print("\n" + "=" * 60)
    print("🚀 完整流水线测试")
    print("=" * 60)
    
    print(f"\n📁 输入文件: {parsed_path}")
    if force_types:
        print(f"📌 强制类型: {force_types}")
    
    print("\n🔄 正在执行流水线...")
    result = run_pipeline_from_file(parsed_path, force_types)
    
    print("\n📊 执行结果:")
    print(f"  - 标题: {result.title}")
    print(f"  - 路由类型: {result.routed_types}")
    print(f"  - 总 Tokens: {result.total_tokens}")
    
    print("\n✅ 成功抽取:")
    for type_id, artifact in result.artifacts.items():
        print(f"  - {type_id}:")
        # 显示摘要
        if type_id == 'dfd':
            processes = artifact.get('processes', [])
            flows = artifact.get('data_flows', [])
            print(f"      Processes: {len(processes)}, Data Flows: {len(flows)}")
        elif type_id == 'concepts':
            concepts = (artifact.get('generation_knowledge', {}).get('concepts', []))
            print(f"      Concepts: {len(concepts)}")
        elif type_id == 'rules':
            rules = (artifact.get('generation_knowledge', {}).get('rules', []))
            print(f"      Rules: {len(rules)}")
        else:
            print(f"      Keys: {list(artifact.keys())[:5]}")
    
    if result.errors:
        print("\n❌ 错误:")
        for type_id, error in result.errors.items():
            print(f"  - {type_id}: {error}")
    
    # 保存结果
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    # 保存 artifacts
    for type_id, artifact in result.artifacts.items():
        output_file = output_dir / f"pipeline_{type_id}.json"
        output_file.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n💾 已保存: {output_file}")
    
    # 保存 trace
    trace_file = output_dir / "pipeline_trace.json"
    trace_file.write_text(json.dumps(result.trace, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"💾 已保存: {trace_file}")
    
    print(f"\n📋 摘要: {result.summary()}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="测试两阶段抽取流水线")
    parser.add_argument("parsed_path", nargs="?", help="parsed.json 文件路径")
    parser.add_argument("--force-types", "-t", help="强制指定类型（逗号分隔）")
    parser.add_argument("--registry", "-r", action="store_true", help="只显示类型注册表")
    parser.add_argument("--router-only", action="store_true", help="只测试路由器")
    
    args = parser.parse_args()
    
    if args.registry:
        test_type_registry()
        return
    
    # 默认测试文件
    parsed_path = args.parsed_path
    if not parsed_path:
        default_files = list(Path("data/parsed").glob("*数据流图*.json"))
        if default_files:
            parsed_path = str(default_files[0])
        else:
            print("❌ 请提供 parsed.json 文件路径")
            return
    
    if not Path(parsed_path).exists():
        print(f"❌ 文件不存在: {parsed_path}")
        return
    
    if args.router_only:
        test_router(parsed_path)
    else:
        force_types = args.force_types.split(',') if args.force_types else None
        test_full_pipeline(parsed_path, force_types)


if __name__ == "__main__":
    main()

