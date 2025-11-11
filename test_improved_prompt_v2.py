#!/usr/bin/env python3
"""
测试优化后的requirement_analysis提示词效果
"""

import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import extract_universal_knowledge

def test_improved_requirement_analysis():
    """测试改进后的requirement_analysis提示词"""
    
    print("=== 测试优化后的requirement_analysis提示词 ===")
    
    # 读取之前保存的内容和元数据
    try:
        with open('temp_content.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open('temp_metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        print(f"内容长度: {len(content)} 字符")
        print(f"元数据: {metadata}")
        
    except FileNotFoundError as e:
        print(f"错误：找不到测试文件 {e}")
        return False
    
    # 调用extract_universal_knowledge工具
    try:
        print("\n调用extract_universal_knowledge工具...")
        result = extract_universal_knowledge(
            content=content,
            url=metadata.get('url', ''),
            title=metadata.get('title', ''),
            requirement_type="需求分析",
            target_conversion_type="通用知识库"
        )
        
        # 保存结果
        output_file = 'improved_requirement_analysis_result_v2.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        
        print(f"结果已保存到: {output_file}")
        
        # 解析JSON结果进行验证
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return False
        
        # 验证结果结构
        if validate_result_structure(result_data):
            print("✅ 结果结构验证通过")
            return True
        else:
            print("❌ 结果结构验证失败")
            return False
            
    except Exception as e:
        print(f"错误：调用extract_universal_knowledge失败 - {e}")
        return False

def validate_result_structure(result):
    """验证结果结构和最小输出量"""
    
    print("\n=== 结构验证和最小输出量检查 ===")
    
    # 检查是否有success字段和knowledge_base
    if not result.get('success'):
        print("❌ 提取失败")
        return False
        
    knowledge_base = result.get('knowledge_base', {})
    if not knowledge_base:
        print("❌ 缺少knowledge_base字段")
        return False
    
    # 检查基本结构
    required_keys = ['generation_knowledge', 'validation_knowledge', 'examples']
    for key in required_keys:
        if key not in knowledge_base:
            print(f"❌ 缺少必需字段: {key}")
            return False
    
    # 检查generation_knowledge子字段
    gen_knowledge = knowledge_base.get('generation_knowledge', {})
    gen_required = ['concepts', 'rules', 'patterns', 'transformations']
    
    for key in gen_required:
        if key not in gen_knowledge:
            print(f"❌ generation_knowledge缺少字段: {key}")
            return False
    
    # 检查validation_knowledge子字段
    val_knowledge = knowledge_base.get('validation_knowledge', {})
    val_required = ['criteria', 'checklist', 'error_patterns']
    
    for key in val_required:
        if key not in val_knowledge:
            print(f"❌ validation_knowledge缺少字段: {key}")
            return False
    
    # 检查最小输出量要求
    min_requirements = {
        'concepts': 5,
        'rules': 4,
        'patterns': 3,
        'transformations': 2,
        'criteria': 5,
        'checklist': 3,
        'error_patterns': 3,
        'input_examples': 3
    }
    
    # 统计各部分数量
    counts = {
        'concepts': len(gen_knowledge.get('concepts', [])),
        'rules': len(gen_knowledge.get('rules', [])),
        'patterns': len(gen_knowledge.get('patterns', [])),
        'transformations': len(gen_knowledge.get('transformations', [])),
        'criteria': len(val_knowledge.get('criteria', [])),
        'checklist': len(val_knowledge.get('checklist', [])),
        'error_patterns': len(val_knowledge.get('error_patterns', [])),
        'input_examples': len(knowledge_base.get('examples', {}).get('input_examples', []))
    }
    
    print("\n各部分提取数量:")
    all_passed = True
    for key, count in counts.items():
        min_required = min_requirements[key]
        status = "✅" if count >= min_required else "❌"
        print(f"{status} {key}: {count}条 (最少需要{min_required}条)")
        if count < min_required:
            all_passed = False
    
    # 显示第一个概念的详细内容（如果存在）
    if counts['concepts'] > 0:
        first_concept = gen_knowledge['concepts'][0]
        print(f"\n第一个概念详细内容:")
        print(f"  ID: {first_concept.get('concept_id', 'N/A')}")
        print(f"  Name: {first_concept.get('name', 'N/A')}")
        print(f"  Definition: {first_concept.get('definition', 'N/A')[:100]}...")
    
    # 显示第一个规则的详细内容（如果存在）
    if counts['rules'] > 0:
        first_rule = gen_knowledge['rules'][0]
        print(f"\n第一个规则详细内容:")
        print(f"  ID: {first_rule.get('rule_id', 'N/A')}")
        print(f"  Type: {first_rule.get('type', 'N/A')}")
        print(f"  Condition: {first_rule.get('condition', 'N/A')}")
        print(f"  Action: {first_rule.get('action', 'N/A')}")
    
    return all_passed

if __name__ == "__main__":
    success = test_improved_requirement_analysis()
    if success:
        print("\n🎉 测试成功！优化后的提示词工作正常。")
    else:
        print("\n💥 测试失败！需要进一步优化提示词。")