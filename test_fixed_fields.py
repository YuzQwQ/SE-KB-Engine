#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试修复后的patterns和checklist字段生成效果
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from universal_knowledge_processor import UniversalKnowledgeProcessor

def test_fixed_patterns_and_checklist():
    """测试修复后的patterns和checklist生成"""
    
    # 创建处理器实例
    processor = UniversalKnowledgeProcessor()
    
    # 测试内容 - 包含之前有问题的模式
    test_content = """
    基于 CASE 工具的需求一致性分析
    
    一、需求分析概述
    需求分析是软件工程中的重要环节，用于确定系统的功能和非功能需求。
    
    二、CASE工具介绍
    CASE（Computer-Aided Software Engineering）工具是计算机辅助软件工程工具。
    
    三、一致性分析方法
    1. 检查需求之间的逻辑一致性
    2. 验证需求的完整性
    3. 确保需求的可追溯性
    
    四、通过原型完善用户需求
    原型方法是一种有效的需求获取和验证方法。
    
    五、结构化分析建模
    结构化分析建模包括数据流图、实体关系图等建模方法。
    
    检查清单：
    1. 需求文档是否完整
    2. 需求是否具有可测试性
    3. 需求优先级是否明确
    • 检查需求的一致性
    • 验证需求的可行性
    - 确认用户接受度
    """
    
    print("=== 测试修复后的字段生成效果 ===\n")
    
    # 测试patterns提取
    print("1. 测试patterns字段：")
    patterns = processor._extract_patterns(test_content)
    print(f"提取到 {len(patterns)} 个模式：")
    for i, pattern in enumerate(patterns, 1):
        print(f"  模式 {i}:")
        print(f"    ID: {pattern['pattern_id']}")
        print(f"    名称: {pattern['name']}")
        print(f"    模板: {pattern['template'][:50]}...")
        print(f"    使用场景: {pattern['usage_context']}")
        print()
    
    # 测试checklist提取
    print("2. 测试checklist字段：")
    checklist = processor._extract_checklist(test_content)
    print(f"提取到 {len(checklist)} 个检查项：")
    for i, check in enumerate(checklist, 1):
        print(f"  检查项 {i}:")
        print(f"    ID: {check['check_id']}")
        print(f"    描述: {check['description']}")
        print(f"    类别: {check['category']}")
        print(f"    验证方法: {check['validation_method']}")
        print()
    
    # 测试完整的知识库生成
    print("3. 测试完整知识库生成：")
    knowledge_base = processor.extract_knowledge(
        content=test_content,
        url="https://test.example.com",
        title="测试文档",
        requirement_type="universal_knowledge",
        target_conversion_type="knowledge_base"
    )
    
    print(f"生成的知识库包含：")
    print(f"  - 概念数量: {len(knowledge_base['generation_knowledge']['concepts'])}")
    print(f"  - 模式数量: {len(knowledge_base['generation_knowledge']['patterns'])}")
    print(f"  - 检查清单数量: {len(knowledge_base['validation_knowledge']['checklist'])}")
    print(f"  - 规则数量: {len(knowledge_base['generation_knowledge']['rules'])}")
    
    # 验证修复效果
    print("\n=== 修复效果验证 ===")
    
    # 检查patterns是否还有问题
    patterns_issues = []
    for pattern in knowledge_base['generation_knowledge']['patterns']:
        if "四、" in pattern['name'] or "通过原型完善用户需求" in pattern['name']:
            patterns_issues.append(f"模式名称仍包含章节标记: {pattern['name']}")
        if len(pattern['name']) > 20:
            patterns_issues.append(f"模式名称过长: {pattern['name']}")
    
    # 检查checklist是否还有问题
    checklist_issues = []
    for check in knowledge_base['validation_knowledge']['checklist']:
        if check['description'] in ['796463",', 'json",'] or len(check['description']) < 5:
            checklist_issues.append(f"检查项描述无效: {check['description']}")
    
    if patterns_issues:
        print("❌ Patterns字段仍存在问题：")
        for issue in patterns_issues:
            print(f"  - {issue}")
    else:
        print("✅ Patterns字段问题已修复")
    
    if checklist_issues:
        print("❌ Checklist字段仍存在问题：")
        for issue in checklist_issues:
            print(f"  - {issue}")
    else:
        print("✅ Checklist字段问题已修复")
    
    print(f"\n总体评估：")
    print(f"  - 模式提取质量: {'优秀' if not patterns_issues else '需要改进'}")
    print(f"  - 检查清单质量: {'优秀' if not checklist_issues else '需要改进'}")
    
    return knowledge_base

if __name__ == "__main__":
    test_fixed_patterns_and_checklist()