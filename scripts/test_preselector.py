"""
测试 LLM Preselector 的效果

用法:
    python scripts/test_preselector.py [parsed_json_path]
    
示例:
    python scripts/test_preselector.py "data/parsed/blog_csdn_net_软件工程 -- 数据流图的画法_数据流图怎么画-CSDN博客_parsed_20251203_162200.json"
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.llm_preselector import LLMPreselector, preselect_candidates


def test_preselector(parsed_path: str = None):
    """测试 preselector"""
    
    # 默认测试文件
    if not parsed_path:
        default_files = list(Path("data/parsed").glob("*数据流图*.json"))
        if default_files:
            parsed_path = str(default_files[0])
        else:
            parsed_path = "data/parsed/blog_csdn_net_软件工程 -- 数据流图的画法_数据流图怎么画-CSDN博客_parsed_20251203_162200.json"
    
    print("=" * 60)
    print(f"测试文件: {parsed_path}")
    print("=" * 60)
    
    # 加载数据
    try:
        parsed_data = json.loads(Path(parsed_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"❌ 文件不存在: {parsed_path}")
        return
    
    print(f"\n📄 标题: {parsed_data.get('title', 'N/A')}")
    print(f"🔗 URL: {parsed_data.get('source_url', 'N/A')}")
    print(f"📝 正文长度: {len(parsed_data.get('clean_text', ''))} 字符")
    print(f"📑 Sections: {len(parsed_data.get('sections', []))} 个")
    
    # 测试 preselector
    print(f"\n{'=' * 60}")
    print("🔍 调用 LLM Preselector...")
    print(f"{'=' * 60}")
    
    preselector = LLMPreselector()
    
    print("\n配置信息:")
    print(f"  - BASE_URL: {preselector.base_url[:50]}..." if preselector.base_url else "  - BASE_URL: 未配置")
    print(f"  - MODEL: {preselector.model_id}")
    print(f"  - MAX_INPUT: {preselector.max_input_chars} chars")
    
    if not preselector.base_url or not preselector.api_key:
        print("\n⚠️ 未配置 FILTER_BASE_URL 或 FILTER_API_KEY，请检查 .env 文件")
        return
    
    # 执行预筛选
    candidates, trace = preselector.preselect(parsed_data)
    
    print("\n📊 筛选结果:")
    print(f"  - 总候选数: {len(candidates)}")
    print(f"  - DFD 相关: {len([c for c in candidates if c.type == 'dfd'])}")
    print(f"  - 概念定义: {len([c for c in candidates if c.type == 'concept'])}")
    print(f"  - 规则约束: {len([c for c in candidates if c.type == 'rule'])}")
    print(f"  - Unknown: {len([c for c in candidates if c.type == 'unknown'])}")
    
    if trace.get('error'):
        print(f"\n❌ 错误: {trace}")
        return
    
    print("\n🔧 Trace:")
    print(f"  - Provider: {trace.get('provider', 'N/A')}")
    print(f"  - Tokens: {trace.get('tokens', 'N/A')}")
    
    # 显示候选详情
    print(f"\n{'=' * 60}")
    print("📋 候选片段详情:")
    print(f"{'=' * 60}")
    
    for i, c in enumerate(candidates[:10]):  # 只显示前10个
        print(f"\n[{i+1}] Type: {c.type.upper()}")
        print(f"    Text: {c.text[:200]}..." if len(c.text) > 200 else f"    Text: {c.text}")
    
    if len(candidates) > 10:
        print(f"\n... 还有 {len(candidates) - 10} 个候选未显示")
    
    # 按类型测试
    print(f"\n{'=' * 60}")
    print("🎯 按类型筛选测试:")
    print(f"{'=' * 60}")
    
    for target_type in ['dfd', 'concepts', 'rules']:
        cands, t, score = preselect_candidates(parsed_data, target_type)
        print(f"\n  [{target_type}] 候选数: {len(cands)}, 得分: {score:.2f}")
    
    print("\n✅ 测试完成!")


def compare_with_legacy(parsed_path: str = None):
    """对比新旧 adapter 的效果"""
    
    if not parsed_path:
        default_files = list(Path("data/parsed").glob("*数据流图*.json"))
        if default_files:
            parsed_path = str(default_files[0])
        else:
            return
    
    parsed_data = json.loads(Path(parsed_path).read_text(encoding="utf-8"))
    text = parsed_data.get("clean_text", "")
    ctx = {
        "url": parsed_data.get("source_url", ""),
        "title": parsed_data.get("title", ""),
        "_parsed_data": parsed_data,
    }
    
    print(f"\n{'=' * 60}")
    print("📊 Legacy vs Enhanced Adapter 对比")
    print(f"{'=' * 60}")
    
    # Legacy DFD
    from adapters.dfd_adapter import DFDAdapter
    legacy_adapter = DFDAdapter()
    legacy_cands, legacy_trace, legacy_metrics, legacy_score = legacy_adapter.build_candidates(text, ctx)
    
    print("\n🔴 Legacy DFDAdapter:")
    print(f"   候选数: {len(legacy_cands)}")
    print(f"   得分: {legacy_score:.2f}")
    print(f"   候选内容: {[c.get('text', '')[:50] for c in legacy_cands]}")
    
    # Enhanced DFD
    from adapters.enhanced_adapters import EnhancedDFDAdapter
    enhanced_adapter = EnhancedDFDAdapter()
    enhanced_cands, enhanced_trace, enhanced_metrics, enhanced_score = enhanced_adapter.build_candidates(text, ctx)
    
    print("\n🟢 Enhanced DFDAdapter:")
    print(f"   候选数: {len(enhanced_cands)}")
    print(f"   得分: {enhanced_score:.2f}")
    print(f"   DFD 类型: {len([c for c in enhanced_cands if c.get('type') == 'dfd'])}")
    
    print("\n📈 提升:")
    print(f"   候选数: {len(legacy_cands)} → {len(enhanced_cands)} (+{len(enhanced_cands) - len(legacy_cands)})")
    print(f"   得分: {legacy_score:.2f} → {enhanced_score:.2f}")


if __name__ == "__main__":
    parsed_path = sys.argv[1] if len(sys.argv) > 1 else None
    test_preselector(parsed_path)
    
    # 可选：对比测试
    # compare_with_legacy(parsed_path)

