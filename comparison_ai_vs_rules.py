#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI方法与规则方法知识提取对比测试
"""

import json
import time
from datetime import datetime
from server import extract_knowledge_with_ai, extract_universal_knowledge

def load_test_data():
    """加载测试数据"""
    try:
        # 加载测试内容
        with open('temp_content.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 加载元数据
        with open('temp_metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return content, metadata
    except Exception as e:
        print(f"❌ 加载测试数据失败: {e}")
        return None, None

def evaluate_extraction_result(result_json, method_name):
    """评估提取结果的质量"""
    try:
        result = json.loads(result_json)
        
        if not result.get('success', False):
            print(f"❌ {method_name} 提取失败: {result.get('message', '未知错误')}")
            return {
                'success': False,
                'total_items': 0,
                'categories': {},
                'score': 0.0
            }
        
        knowledge_base = result.get('knowledge_base', {})
        gen_knowledge = knowledge_base.get('generation_knowledge', {})
        
        # 统计各类别的数量
        categories = {
            'concepts': len(gen_knowledge.get('concepts', [])),
            'rules': len(gen_knowledge.get('rules', [])),
            'patterns': len(gen_knowledge.get('patterns', [])),
            'transformations': len(gen_knowledge.get('transformations', [])),
            'criteria': len(gen_knowledge.get('criteria', [])),
            'input_examples': len(gen_knowledge.get('input_examples', []))
        }
        
        total_items = sum(categories.values())
        
        # 计算评分（每个类别至少3个才算达标）
        qualified_categories = sum(1 for count in categories.values() if count >= 3)
        score = (qualified_categories / len(categories)) * 100
        
        return {
            'success': True,
            'total_items': total_items,
            'categories': categories,
            'qualified_categories': qualified_categories,
            'score': score
        }
        
    except Exception as e:
        print(f"❌ 评估{method_name}结果失败: {e}")
        return {
            'success': False,
            'total_items': 0,
            'categories': {},
            'score': 0.0
        }

def run_comparison_test():
    """运行对比测试"""
    print("=" * 80)
    print("🔬 AI方法 vs 规则方法 知识提取对比测试")
    print("=" * 80)
    
    # 加载测试数据
    content, metadata = load_test_data()
    if not content or not metadata:
        return
    
    print(f"📄 测试内容长度: {len(content)} 字符")
    print(f"📋 测试文档: {metadata.get('title', '未知标题')}")
    print()
    
    # 为了公平对比，使用相同长度的内容
    test_content = content[:3000]  # 使用前3000字符
    
    results = {}
    
    # 测试AI方法
    print("🤖 测试AI驱动方法...")
    start_time = time.time()
    try:
        ai_result = extract_knowledge_with_ai(
            content=test_content,
            url=metadata.get('url', ''),
            title=metadata.get('title', ''),
            prompt_type='universal_knowledge'
        )
        ai_time = time.time() - start_time
        ai_evaluation = evaluate_extraction_result(ai_result, "AI方法")
        results['ai'] = {
            'result': ai_result,
            'evaluation': ai_evaluation,
            'time_cost': ai_time
        }
        print(f"✅ AI方法完成，耗时: {ai_time:.2f}秒")
        
        # 保存AI结果
        with open('comparison_ai_result.json', 'w', encoding='utf-8') as f:
            f.write(ai_result)
            
    except Exception as e:
        print(f"❌ AI方法测试失败: {e}")
        results['ai'] = {
            'result': None,
            'evaluation': {'success': False, 'score': 0.0},
            'time_cost': 0
        }
    
    print()
    
    # 测试规则方法
    print("📏 测试规则驱动方法...")
    start_time = time.time()
    try:
        rules_result = extract_universal_knowledge(
            content=test_content,
            url=metadata.get('url', ''),
            title=metadata.get('title', ''),
            requirement_type='软件需求分析',
            target_conversion_type='知识库'
        )
        rules_time = time.time() - start_time
        rules_evaluation = evaluate_extraction_result(rules_result, "规则方法")
        results['rules'] = {
            'result': rules_result,
            'evaluation': rules_evaluation,
            'time_cost': rules_time
        }
        print(f"✅ 规则方法完成，耗时: {rules_time:.2f}秒")
        
        # 保存规则结果
        with open('comparison_rules_result.json', 'w', encoding='utf-8') as f:
            f.write(rules_result)
            
    except Exception as e:
        print(f"❌ 规则方法测试失败: {e}")
        results['rules'] = {
            'result': None,
            'evaluation': {'success': False, 'score': 0.0},
            'time_cost': 0
        }
    
    print()
    
    # 生成对比报告
    generate_comparison_report(results)
    
    return results

def generate_comparison_report(results):
    """生成对比报告"""
    print("📊 对比测试报告")
    print("=" * 80)
    
    ai_eval = results['ai']['evaluation']
    rules_eval = results['rules']['evaluation']
    
    print("🎯 总体评分对比:")
    print(f"   AI方法:   {ai_eval['score']:.1f}% ({ai_eval.get('qualified_categories', 0)}/6 类别达标)")
    print(f"   规则方法: {rules_eval['score']:.1f}% ({rules_eval.get('qualified_categories', 0)}/6 类别达标)")
    
    if ai_eval['score'] > rules_eval['score']:
        print("🏆 AI方法胜出！")
    elif rules_eval['score'] > ai_eval['score']:
        print("🏆 规则方法胜出！")
    else:
        print("🤝 两种方法平分秋色")
    
    print()
    print("⏱️ 性能对比:")
    print(f"   AI方法耗时:   {results['ai']['time_cost']:.2f}秒")
    print(f"   规则方法耗时: {results['rules']['time_cost']:.2f}秒")
    
    print()
    print("📈 详细统计对比:")
    print(f"{'类别':<15} {'AI方法':<10} {'规则方法':<10} {'优势':<10}")
    print("-" * 50)
    
    categories = ['concepts', 'rules', 'patterns', 'transformations', 'criteria', 'input_examples']
    
    for category in categories:
        ai_count = ai_eval.get('categories', {}).get(category, 0)
        rules_count = rules_eval.get('categories', {}).get(category, 0)
        
        if ai_count > rules_count:
            advantage = "AI"
        elif rules_count > ai_count:
            advantage = "规则"
        else:
            advantage = "平分"
        
        print(f"{category:<15} {ai_count:<10} {rules_count:<10} {advantage:<10}")
    
    print()
    print("💡 结论和建议:")
    
    if ai_eval['score'] > rules_eval['score']:
        print("✅ AI方法在知识提取质量上优于规则方法")
        print("📝 建议: 继续优化AI提示词，提高提取的完整性")
    elif rules_eval['score'] > ai_eval['score']:
        print("⚠️  规则方法在当前测试中表现更好")
        print("📝 建议: 需要进一步优化AI方法的提示词和参数")
    else:
        print("🤔 两种方法各有优势，需要根据具体场景选择")
    
    if results['ai']['time_cost'] < results['rules']['time_cost']:
        print("⚡ AI方法在处理速度上有优势")
    else:
        print("⚡ 规则方法在处理速度上有优势")
    
    # 保存对比报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'ai_evaluation': ai_eval,
        'rules_evaluation': rules_eval,
        'ai_time_cost': results['ai']['time_cost'],
        'rules_time_cost': results['rules']['time_cost'],
        'conclusion': {
            'quality_winner': 'AI' if ai_eval['score'] > rules_eval['score'] else 'Rules' if rules_eval['score'] > ai_eval['score'] else 'Tie',
            'speed_winner': 'AI' if results['ai']['time_cost'] < results['rules']['time_cost'] else 'Rules'
        }
    }
    
    with open('comparison_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细报告已保存到: comparison_report.json")

if __name__ == "__main__":
    run_comparison_test()