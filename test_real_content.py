#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('scripts')
from universal_knowledge_processor import UniversalKnowledgeProcessor

def test_real_content():
    """使用真实的CSDN文章内容测试改进后的概念提取逻辑"""
    
    # 创建处理器实例
    processor = UniversalKnowledgeProcessor()
    
    # 真实的CSDN文章内容片段
    real_content = '''
软件工程之软件需求分析

一、需求分析任务
1.用户需求
2.系统需求
（1）功能需求
（2）数据需求
（3）其他需求

二、需求分析过程

三、用户需求获取
1.研究用户
2.从调查中获取用户需求
3.通过原型完善用户需求

四、结构化分析建模
1.功能层次模型
2.数据流模型
（1）数据流图特点
（2）数据流图的用途
（3）数据流细化过程
（4）数据流图中符号的命名
（5）数据流图中的数据字典

3.数据关系模型(ER图)
（1）数据实体
（2）数据关系
（3）数据属性

4.系统状态模型
（1）状态图特点
（2）状态图应用举例

五、需求有效性验证
1.需求验证内容
（1）有效性验证
（2）一致性验证
（3）完整性验证
（4）现实性验证
（5）可检验性验证

2.需求验证方法
1.需求评审
2.需求原型评价
3.基于CASE工具的需求一致性分析

六、需求规格定义

需求分析是指对软件系统功能和性能要求的详细分析过程。
数据流图（DFD）是指描述系统中数据流动的图形化表示方法。
CASE工具是指计算机辅助软件工程工具，用于支持软件开发过程。
一致性验证是指检查需求规格说明书中各部分内容的一致性。
软件工程是指应用系统化、规范化、可量化的方法来开发、运营和维护软件。
'''
    
    print("=== 使用真实CSDN文章内容测试改进后的概念提取逻辑 ===\n")
    print("文章内容片段:")
    print(real_content[:500] + "...")
    print("\n" + "="*60 + "\n")
    
    # 提取概念
    concepts = processor._extract_concepts(real_content)
    
    print(f"提取到的概念数量: {len(concepts)}\n")
    
    for i, concept in enumerate(concepts, 1):
        print(f"{i}. 概念名称: {concept['name']}")
        print(f"   概念定义: {concept['definition']}")
        print(f"   概念ID: {concept['concept_id']}")
        print(f"   类别: {concept['category']}")
        
        # 分析改进效果
        if concept['name'] != "未知概念" and len(concept['name']) <= 30:
            print("   ✅ 概念名称识别准确")
        else:
            print("   ❌ 概念名称识别有问题")
            
        if concept['definition'].endswith(('.', '。', '!', '！', '?', '？')):
            print("   ✅ 定义格式规范")
        else:
            print("   ❌ 定义格式需要改进")
            
        print("-" * 50)

if __name__ == "__main__":
    test_real_content()