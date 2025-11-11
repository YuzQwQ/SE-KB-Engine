#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CSDN网页爬取和HTML标题结构保留功能
"""

import requests
import json
from utils.html_cleaner import clean_html_with_structure, is_html_content, html_cleaner

def test_csdn_crawl():
    """测试CSDN网页爬取"""
    print("=== 测试CSDN网页爬取 ===\n")
    
    url = "https://blog.csdn.net/weixin_34640289/article/details/142647843"
    
    # 调用本地MCP服务器的爬取接口
    server_url = 'http://127.0.0.1:8010/api/crawl'
    data = {'url': url}
    
    try:
        print(f"正在爬取: {url}")
        response = requests.post(server_url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ 爬取成功!")
            print(f"标题: {result.get('title', '未获取到标题')}")
            print(f"内容长度: {len(result.get('content', ''))} 字符")
            print(f"URL: {result.get('url', '')}")
            
            # 保存原始结果
            with open('csdn_crawl_result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("✓ 原始结果已保存到 csdn_crawl_result.json")
            
            return result
            
        else:
            print(f"✗ 爬取失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return None

def test_html_structure_processing(crawl_result):
    """测试HTML结构处理"""
    if not crawl_result:
        print("没有爬取结果，跳过HTML结构处理测试")
        return
    
    print("\n=== 测试HTML结构处理 ===\n")
    
    content = crawl_result.get('content', '')
    
    # 1. 检测是否为HTML内容
    print("1. HTML内容检测:")
    is_html = is_html_content(content)
    print(f"   是否为HTML内容: {is_html}")
    
    if not is_html:
        print("   内容不是HTML格式，无法测试标题结构提取")
        return
    
    # 2. 进行结构化清理
    print("\n2. 结构化清理:")
    cleaning_result = clean_html_with_structure(content)
    
    print(f"   原始内容长度: {len(content)} 字符")
    print(f"   清理后长度: {len(cleaning_result['cleaned_content'])} 字符")
    print(f"   提取标题数量: {len(cleaning_result['title_structure'])}")
    
    # 3. 显示提取的标题结构
    print("\n3. 提取的标题结构:")
    if cleaning_result['title_structure']:
        for i, title in enumerate(cleaning_result['title_structure'], 1):
            print(f"   {i}. [H{title['level']}] {title['text']}")
    else:
        print("   未提取到标题结构")
    
    # 4. 生成标题上下文
    print("\n4. 标题上下文生成:")
    if cleaning_result['title_structure']:
        title_context = html_cleaner.format_title_structure_as_context(
            cleaning_result['title_structure']
        )
        print("   生成的上下文:")
        print(title_context)
    else:
        print("   无标题结构，无法生成上下文")
    
    # 5. 显示处理后的内容片段
    print("\n5. 处理后内容片段 (前300字符):")
    print(cleaning_result['cleaned_content'][:300])
    if len(cleaning_result['cleaned_content']) > 300:
        print("...")
    
    # 保存处理结果
    processing_result = {
        'original_length': len(content),
        'cleaned_length': len(cleaning_result['cleaned_content']),
        'title_count': len(cleaning_result['title_structure']),
        'title_structure': cleaning_result['title_structure'],
        'cleaned_content': cleaning_result['cleaned_content'][:1000],  # 只保存前1000字符
        'title_context': html_cleaner.format_title_structure_as_context(
            cleaning_result['title_structure']
        ) if cleaning_result['title_structure'] else ""
    }
    
    with open('csdn_html_processing_result.json', 'w', encoding='utf-8') as f:
        json.dump(processing_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 处理结果已保存到 csdn_html_processing_result.json")
    
    return processing_result

def test_ai_knowledge_extraction(processing_result):
    """测试AI知识提取（模拟）"""
    if not processing_result:
        print("没有处理结果，跳过AI知识提取测试")
        return
    
    print("\n=== 模拟AI知识提取 ===\n")
    
    # 构建AI输入内容
    title_context = processing_result.get('title_context', '')
    cleaned_content = processing_result.get('cleaned_content', '')
    
    ai_input = f"{title_context}\n\n{cleaned_content}" if title_context else cleaned_content
    
    print(f"AI输入内容长度: {len(ai_input)} 字符")
    print(f"包含标题上下文: {'是' if title_context else '否'}")
    
    if title_context:
        print(f"标题上下文长度: {len(title_context)} 字符")
    
    print("\nAI输入内容预览 (前500字符):")
    print(ai_input[:500])
    if len(ai_input) > 500:
        print("...")
    
    # 保存AI输入内容
    ai_input_data = {
        'input_length': len(ai_input),
        'has_title_context': bool(title_context),
        'title_context_length': len(title_context) if title_context else 0,
        'ai_input_preview': ai_input[:1000],  # 保存前1000字符预览
        'full_input': ai_input  # 完整输入内容
    }
    
    with open('csdn_ai_input.json', 'w', encoding='utf-8') as f:
        json.dump(ai_input_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ AI输入数据已保存到 csdn_ai_input.json")

def main():
    """主测试函数"""
    print("开始测试CSDN网页爬取和HTML标题结构处理...\n")
    
    try:
        # 步骤1: 爬取网页
        crawl_result = test_csdn_crawl()
        
        # 步骤2: 处理HTML结构
        processing_result = test_html_structure_processing(crawl_result)
        
        # 步骤3: 模拟AI知识提取
        test_ai_knowledge_extraction(processing_result)
        
        print("\n" + "=" * 60)
        print("=== 测试完成 ===")
        
        if crawl_result and processing_result:
            print("✓ 网页爬取: 成功")
            print(f"✓ HTML处理: 提取到 {processing_result['title_count']} 个标题")
            print(f"✓ 内容清理: {processing_result['original_length']} → {processing_result['cleaned_length']} 字符")
            print("✓ AI输入准备: 完成")
            print("\n所有功能正常工作！")
        else:
            print("✗ 部分功能测试失败，请检查错误信息")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()