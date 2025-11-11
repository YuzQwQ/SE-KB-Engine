#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('scripts')
from universal_knowledge_processor import UniversalKnowledgeProcessor

def test_concept_extraction():
    """测试改进后的概念提取逻辑"""
    
    # 创建处理器实例
    processor = UniversalKnowledgeProcessor()
    
    # 测试文本
    test_content = '''
数据流图（DFD）是指描述系统中数据流动的图形化表示方法。
需求分析是指对系统功能和性能要求的详细分析过程。
CASE工具表示计算机辅助软件工程工具，用于支持软件开发过程。
一致性分析是指检查需求规格说明书中各部分内容的一致性。
软件工程是指应用系统化、规范化、可量化的方法来开发、运营和维护软件。
'''
    
    print("=== 测试改进后的概念提取逻辑 ===\n")
    print("测试文本:")
    print(test_content)
    print("\n" + "="*50 + "\n")
    
    # 提取概念
    concepts = processor._extract_concepts(test_content)
    
    print(f"提取到的概念数量: {len(concepts)}\n")
    
    for i, concept in enumerate(concepts, 1):
        print(f"{i}. 概念名称: {concept['name']}")
        print(f"   概念定义: {concept['definition']}")
        print(f"   概念ID: {concept['concept_id']}")
        print(f"   类别: {concept['category']}")
        print("-" * 40)

if __name__ == "__main__":
    test_concept_extraction()