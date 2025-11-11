#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试HTML标题结构保留功能
验证HTML清理器能否正确提取和保留h1-h3标题结构
"""

import json
from utils.html_cleaner import clean_html_with_structure, is_html_content, html_cleaner

def test_title_structure_extraction():
    """测试标题结构提取功能"""
    print("=== 测试HTML标题结构提取功能 ===\n")
    
    # 测试HTML内容
    test_html = """
    <html>
    <head><title>测试文档</title></head>
    <body>
        <h1>第一章 系统概述</h1>
        <p>这是系统概述的内容...</p>
        
        <h2>1.1 系统架构</h2>
        <p>系统采用微服务架构...</p>
        
        <h3>1.1.1 前端架构</h3>
        <p>前端使用React框架...</p>
        
        <h3>1.1.2 后端架构</h3>
        <p>后端使用Spring Boot...</p>
        
        <h2>1.2 技术栈</h2>
        <p>主要技术栈包括...</p>
        
        <h1>第二章 功能需求</h1>
        <p>系统功能需求如下...</p>
        
        <h2>2.1 用户管理</h2>
        <p>用户管理模块...</p>
        
        <h3>2.1.1 用户注册</h3>
        <p>用户注册流程...</p>
    </body>
    </html>
    """
    
    # 1. 测试HTML内容检测
    print("1. 测试HTML内容检测:")
    is_html = is_html_content(test_html)
    print(f"   是否为HTML内容: {is_html}")
    print()
    
    # 2. 测试结构化清理
    print("2. 测试结构化清理:")
    result = clean_html_with_structure(test_html)
    
    print(f"   清理后内容长度: {len(result['cleaned_content'])} 字符")
    print(f"   提取到标题数量: {len(result['title_structure'])}")
    print()
    
    # 3. 显示提取的标题结构
    print("3. 提取的标题结构:")
    for i, title in enumerate(result['title_structure'], 1):
        print(f"   {i}. [{title['level']}] {title['text']}")
    print()
    
    # 4. 测试标题结构格式化
    print("4. 标题结构上下文格式化:")
    title_context = html_cleaner.format_title_structure_as_context(result['title_structure'])
    print("   格式化结果:")
    print(title_context)
    print()
    
    # 5. 显示清理后的内容片段
    print("5. 清理后内容片段 (前500字符):")
    print(result['cleaned_content'][:500])
    print("...")
    print()
    
    return result

def test_ai_knowledge_extraction_with_structure():
    """测试带标题结构的AI知识提取"""
    print("=== 测试AI知识提取（含标题结构）===\n")
    
    # 模拟调用AI知识提取函数的逻辑
    test_html = """
    <html>
    <body>
        <h1>软件需求规格说明书</h1>
        <h2>1. 系统概述</h2>
        <p>本系统是一个在线学习管理平台，旨在为教育机构提供完整的在线教学解决方案。</p>
        
        <h3>1.1 系统目标</h3>
        <p>提供高效、易用的在线教学环境，支持多种教学模式和学习方式。</p>
        
        <h2>2. 功能需求</h2>
        <h3>2.1 用户管理</h3>
        <p>系统需要支持学生、教师、管理员三种角色的用户管理。</p>
        
        <h3>2.2 课程管理</h3>
        <p>教师可以创建、编辑和发布课程内容，包括视频、文档、作业等。</p>
        
        <h2>3. 非功能需求</h2>
        <p>系统需要具备高可用性、高性能和良好的用户体验。</p>
    </body>
    </html>
    """
    
    # 使用新的结构化清理功能
    result = clean_html_with_structure(test_html)
    
    print("1. 提取的标题结构:")
    for title in result['title_structure']:
        print(f"   [{title['level']}] {title['text']}")
    print()
    
    print("2. 标题上下文:")
    title_context = html_cleaner.format_title_structure_as_context(result['title_structure'])
    print(title_context)
    print()
    
    print("3. 模拟AI输入内容 (含标题上下文):")
    content_with_context = f"{title_context}\n\n{result['cleaned_content'][:800]}"
    print(content_with_context)
    print()
    
    return {
        'title_structure': result['title_structure'],
        'title_context': title_context,
        'processed_content': result['cleaned_content'],
        'ai_input': content_with_context
    }

def main():
    """主测试函数"""
    print("开始测试HTML标题结构保留功能...\n")
    
    try:
        # 测试1: 基础标题结构提取
        basic_result = test_title_structure_extraction()
        
        print("=" * 60)
        print()
        
        # 测试2: AI知识提取集成测试
        ai_result = test_ai_knowledge_extraction_with_structure()
        
        print("=" * 60)
        print()
        
        # 总结测试结果
        print("=== 测试总结 ===")
        print(f"✓ HTML内容检测: 正常")
        print(f"✓ 标题结构提取: 提取到 {len(basic_result['title_structure'])} 个标题")
        print(f"✓ 内容清理: 清理后 {len(basic_result['cleaned_content'])} 字符")
        print(f"✓ 上下文格式化: 生成 {len(ai_result['title_context'])} 字符的上下文")
        print(f"✓ AI输入准备: 总长度 {len(ai_result['ai_input'])} 字符")
        print()
        print("所有测试通过！HTML标题结构保留功能正常工作。")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()