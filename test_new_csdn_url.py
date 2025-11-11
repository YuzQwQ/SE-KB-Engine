#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from universal_knowledge_processor import UniversalKnowledgeProcessor
from html_cleaner import clean_html_content, is_html_content

def test_new_csdn_url():
    """测试新的CSDN网页知识提取"""
    
    # 目标URL
    url = "https://blog.csdn.net/weixin_34640289/article/details/142647843"
    
    print("🔍 测试新CSDN网页知识提取")
    print("=" * 60)
    print(f"📍 目标URL: {url}")
    
    # 获取网页内容
    print("\n📥 正在获取网页内容...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text
        print(f"✅ 网页内容获取成功，长度: {len(html_content)}")
    except Exception as e:
        print(f"❌ 获取网页内容失败: {e}")
        return
    
    # 清理HTML
    print("\n🧹 正在清理HTML内容...")
    cleaned_content = clean_html_content(html_content)
    print(f"✅ HTML清理完成，长度: {len(cleaned_content)}")
    print(f"📝 清理后内容预览: {cleaned_content[:300]}...")
    
    # 创建知识处理器
    print("\n🔧 创建知识处理器...")
    processor = UniversalKnowledgeProcessor()
    
    # 提取知识库
    print("\n🎯 开始提取知识库...")
    knowledge_base = processor.extract_knowledge(
        content=cleaned_content,
        url=url,
        title="需求分析方法与流程",
        requirement_type="需求管理",
        target_conversion_type="知识库"
    )
    
    # 分析提取结果
    print("\n📊 分析提取结果...")
    concepts = knowledge_base.get('generation_knowledge', {}).get('concepts', [])
    patterns = knowledge_base.get('generation_knowledge', {}).get('patterns', [])
    checklist = knowledge_base.get('validation_knowledge', {}).get('checklist', [])
    
    print(f"\n=== 提取结果分析 ===")
    print(f"概念数量: {len(concepts)}")
    print(f"模式数量: {len(patterns)}")
    print(f"检查项数量: {len(checklist)}")
    
    if concepts:
        print(f"\n概念列表:")
        for i, concept in enumerate(concepts[:5], 1):
            print(f"  {i}. {concept.get('name', 'N/A')}")
    
    if patterns:
        print(f"\n模式列表:")
        for i, pattern in enumerate(patterns[:5], 1):
            print(f"  {i}. {pattern.get('name', 'N/A')}")
    
    if checklist:
        print(f"\n检查项列表:")
        for i, check in enumerate(checklist[:5], 1):
            print(f"  {i}. {check.get('description', 'N/A')[:80]}...")
    
    # 详细展示提取的内容
    if concepts:
        print(f"\n📚 提取的概念:")
        for i, concept in enumerate(concepts, 1):
            name = concept.get('name', '未命名')
            definition = concept.get('definition', '无定义')
            print(f"  概念 {i}:")
            print(f"    名称: {name}")
            print(f"    定义: {definition[:100]}...")
            print(f"    定义长度: {len(definition)} 字符")
    
    if patterns:
        print(f"\n🎨 提取的模式:")
        for i, pattern in enumerate(patterns, 1):
            name = pattern.get('name', '未命名')
            template = pattern.get('template', '无模板')
            print(f"  模式 {i}:")
            print(f"    名称: {name}")
            print(f"    模板: {template[:100]}...")
            print(f"    模板长度: {len(template)} 字符")
    
    if checklist:
        print(f"\n✅ 提取的检查项:")
        valid_count = 0
        for i, check in enumerate(checklist, 1):
            description = check.get('description', '无描述')
            print(f"  检查项 {i}:")
            print(f"    描述: {description}")
            print(f"    描述长度: {len(description)} 字符")
            
            # 简单质量评估
            if len(description) > 5 and not any(invalid in description.lower() for invalid in ['http', 'www.', 'json', 'html']):
                print(f"    质量评估: ✅ 有效")
                valid_count += 1
            else:
                print(f"    质量评估: ❌ 可能无效")
        
        print(f"\n  📈 质量统计:")
        print(f"    有效检查项: {valid_count}/{len(checklist)} ({valid_count/len(checklist)*100:.1f}%)")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_new_csdn_result_{timestamp}.json"
    
    result = {
        "url": url,
        "timestamp": timestamp,
        "content_length": len(cleaned_content),
        "knowledge_base": knowledge_base
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 结果已保存到: {output_file}")
    
    print(f"\n🎯 测试总结:")
    print(f"  - 概念提取: {len(concepts)} 个")
    print(f"  - 模式提取: {len(patterns)} 个")
    print(f"  - 检查清单: {len(checklist)} 个")
    if checklist:
        valid_rate = valid_count/len(checklist)*100
        print(f"  - 检查清单有效率: {valid_rate:.1f}%")

if __name__ == "__main__":
    test_new_csdn_url()