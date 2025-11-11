#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML清理功能测试脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from utils.html_cleaner import HTMLCleaner, clean_html_content
import json

def test_html_cleaner():
    """测试HTML清理功能"""
    print("=== HTML清理功能测试 ===\n")
    
    # 创建清理器实例
    cleaner = HTMLCleaner()
    
    # 测试用例1：包含HTML标签的内容
    test_case_1 = """
    <br /> 8.&#xff08; 销售商&#xff09; 是指向客户销售产品的实体。<br />
    <p>这是一个段落。</p>
    <div>这是一个div标签。</div>
    <strong>这是粗体文本</strong>
    """
    
    print("测试用例1 - 包含HTML标签和实体编码:")
    print(f"原始内容: {repr(test_case_1)}")
    cleaned_1 = clean_html_content(test_case_1)
    print(f"清理后: {repr(cleaned_1)}")
    print(f"清理后内容: {cleaned_1}")
    
    stats_1 = cleaner.get_cleaning_stats(test_case_1, cleaned_1)
    print(f"清理统计: {stats_1}")
    print("-" * 50)
    
    # 测试用例2：包含各种HTML实体编码
    test_case_2 = """
    &#xff08;这是左括号&#xff09;这是右括号
    &#xff1b;这是分号
    &lt;这是小于号&gt;这是大于号
    &amp;这是和号&quot;这是引号&apos;这是撇号
    """
    
    print("测试用例2 - 各种HTML实体编码:")
    print(f"原始内容: {repr(test_case_2)}")
    cleaned_2 = clean_html_content(test_case_2)
    print(f"清理后: {repr(cleaned_2)}")
    print(f"清理后内容: {cleaned_2}")
    
    stats_2 = cleaner.get_cleaning_stats(test_case_2, cleaned_2)
    print(f"清理统计: {stats_2}")
    print("-" * 50)
    
    # 测试用例3：复杂的HTML结构
    test_case_3 = """
    <html>
    <head><title>测试页面</title></head>
    <body>
        <h1>标题</h1>
        <p>这是第一段。<br />这是换行后的内容。</p>
        <ul>
            <li>列表项1</li>
            <li>列表项2</li>
        </ul>
        <script>alert('这是脚本');</script>
        <style>.test { color: red; }</style>
    </body>
    </html>
    """
    
    print("测试用例3 - 复杂HTML结构:")
    print(f"原始内容: {repr(test_case_3)}")
    cleaned_3 = clean_html_content(test_case_3)
    print(f"清理后: {repr(cleaned_3)}")
    print(f"清理后内容: {cleaned_3}")
    
    stats_3 = cleaner.get_cleaning_stats(test_case_3, cleaned_3)
    print(f"清理统计: {stats_3}")
    print("-" * 50)
    
    # 测试用例4：从实际爬取文件中提取的问题内容
    test_case_4 = """
    <br /> 8.&#xff08; 销售商&#xff09; 是指向客户销售产品的实体。销售商可以是零售商、批发商或直销商。<br />
    <br /> 9.&#xff08; 库存管理&#xff09; 是指对产品库存进行跟踪和管理的过程。<br />
    """
    
    print("测试用例4 - 实际问题内容:")
    print(f"原始内容: {repr(test_case_4)}")
    cleaned_4 = clean_html_content(test_case_4)
    print(f"清理后: {repr(cleaned_4)}")
    print(f"清理后内容: {cleaned_4}")
    
    stats_4 = cleaner.get_cleaning_stats(test_case_4, cleaned_4)
    print(f"清理统计: {stats_4}")
    print("-" * 50)
    
    # 测试HTML检测功能
    print("HTML内容检测测试:")
    print(f"测试用例1是否包含HTML: {cleaner.is_html_content(test_case_1)}")
    print(f"测试用例2是否包含HTML: {cleaner.is_html_content(test_case_2)}")
    print(f"纯文本是否包含HTML: {cleaner.is_html_content('这是纯文本内容')}")
    print("-" * 50)

def test_with_real_file():
    """使用实际的爬取文件进行测试"""
    print("=== 实际文件测试 ===\n")
    
    # 测试文件路径
    test_file = r"d:\develop\MCP-develop\mcp-client\shared_data\knowledge_base\dfd_modeling\universal_kb_kb_20251029_170218_99fb3c5a.json"
    
    if not os.path.exists(test_file):
        print(f"测试文件不存在: {test_file}")
        return
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"正在测试文件: {test_file}")
        
        # 检查generation_knowledge中的concepts
        concepts = data.get('generation_knowledge', {}).get('concepts', [])
        
        print(f"找到 {len(concepts)} 个概念")
        
        for i, concept in enumerate(concepts[:3]):  # 只测试前3个
            definition = concept.get('definition', '')
            if definition:
                print(f"\n概念 {i+1} 原始定义:")
                print(f"  {repr(definition)}")
                
                cleaned_definition = clean_html_content(definition)
                print(f"清理后定义:")
                print(f"  {repr(cleaned_definition)}")
                print(f"  内容: {cleaned_definition}")
                
                # 检查是否有改进
                if definition != cleaned_definition:
                    print("  ✓ 内容已清理")
                else:
                    print("  - 内容无需清理")
        
        # 检查transformations中的steps
        transformations = data.get('generation_knowledge', {}).get('transformations', [])
        print(f"\n找到 {len(transformations)} 个转换")
        
        for i, transformation in enumerate(transformations[:2]):  # 只测试前2个
            steps = transformation.get('steps', [])
            print(f"\n转换 {i+1} 包含 {len(steps)} 个步骤")
            
            for j, step in enumerate(steps[:2]):  # 只测试前2个步骤
                # 处理step可能是字符串或字典的情况
                if isinstance(step, dict):
                    step_desc = step.get('description', '')
                elif isinstance(step, str):
                    step_desc = step
                else:
                    step_desc = str(step)
                
                if step_desc:
                    print(f"  步骤 {j+1} 原始描述:")
                    print(f"    {repr(step_desc)}")
                    
                    cleaned_step = clean_html_content(step_desc)
                    print(f"  清理后描述:")
                    print(f"    {repr(cleaned_step)}")
                    print(f"    内容: {cleaned_step}")
                    
                    if step_desc != cleaned_step:
                        print("    ✓ 内容已清理")
                    else:
                        print("    - 内容无需清理")
    
    except Exception as e:
        print(f"测试文件时出错: {str(e)}")

if __name__ == "__main__":
    test_html_cleaner()
    print("\n" + "="*60 + "\n")
    test_with_real_file()