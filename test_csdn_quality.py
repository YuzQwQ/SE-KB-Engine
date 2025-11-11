#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import requests
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.universal_knowledge_processor import UniversalKnowledgeProcessor
from utils.html_cleaner import clean_html_content, is_html_content

def fetch_csdn_content(url):
    """获取CSDN网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"获取网页内容失败: {e}")
        return None

def analyze_knowledge_quality(knowledge_base):
    """分析知识库质量"""
    print("\n" + "="*80)
    print("知识库质量分析")
    print("="*80)
    
    # 基本统计
    concepts = knowledge_base.get('generation_knowledge', {}).get('concepts', [])
    patterns = knowledge_base.get('generation_knowledge', {}).get('patterns', [])
    checklist = knowledge_base.get('validation_knowledge', {}).get('checklist', [])
    
    print(f"\n📊 基本统计:")
    print(f"  - 概念数量: {len(concepts)}")
    print(f"  - 模式数量: {len(patterns)}")
    print(f"  - 检查清单数量: {len(checklist)}")
    
    # 分析patterns字段质量
    print(f"\n🔍 Patterns字段质量分析:")
    if patterns:
        for i, pattern in enumerate(patterns, 1):
            name = pattern.get('name', '')
            template = pattern.get('template', '')
            print(f"  模式 {i}:")
            print(f"    名称: {name}")
            print(f"    名称长度: {len(name)} 字符")
            print(f"    是否包含章节标记: {'是' if any(char.isdigit() and next_char in '、.' for char, next_char in zip(name, name[1:] + ' ')) else '否'}")
            print(f"    模板长度: {len(template)} 字符")
            print(f"    模板预览: {template[:100]}...")
    else:
        print("  ❌ 未提取到任何模式")
    
    # 分析checklist字段质量
    print(f"\n✅ Checklist字段质量分析:")
    if checklist:
        valid_items = 0
        for i, item in enumerate(checklist, 1):
            description = item.get('description', '')
            is_valid = len(description) > 5 and not any(char in description for char in '{}[]"\'') and not description.isdigit()
            if is_valid:
                valid_items += 1
            
            print(f"  检查项 {i}:")
            print(f"    描述: {description}")
            print(f"    描述长度: {len(description)} 字符")
            print(f"    质量评估: {'✅ 有效' if is_valid else '❌ 无效'}")
        
        print(f"\n  📈 质量统计:")
        print(f"    有效检查项: {valid_items}/{len(checklist)} ({valid_items/len(checklist)*100:.1f}%)")
    else:
        print("  ❌ 未提取到任何检查项")
    
    return {
        'concepts_count': len(concepts),
        'patterns_count': len(patterns),
        'checklist_count': len(checklist),
        'valid_checklist_ratio': valid_items/len(checklist) if checklist else 0
    }

def main():
    url = "https://blog.csdn.net/potato_me/article/details/115628364"
    
    print("🚀 开始测试CSDN网页知识库生成质量")
    print(f"📄 目标URL: {url}")
    
    # 获取网页内容
    print("\n📥 正在获取网页内容...")
    html_content = fetch_csdn_content(url)
    
    if not html_content:
        print("❌ 无法获取网页内容")
        return
    
    # 清理HTML内容
    print("🧹 正在清理HTML内容...")
    if is_html_content(html_content):
        cleaned_content = clean_html_content(html_content)
    else:
        cleaned_content = html_content
    
    print(f"📝 清理后内容长度: {len(cleaned_content)} 字符")
    print(f"📝 内容预览: {cleaned_content[:200]}...")
    
    # 生成知识库
    print("\n🔄 正在生成知识库...")
    processor = UniversalKnowledgeProcessor()
    knowledge_base = processor.extract_knowledge(cleaned_content)
    
    # 分析质量
    quality_stats = analyze_knowledge_quality(knowledge_base)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_csdn_quality_result_{timestamp}.json"
    
    result = {
        'url': url,
        'timestamp': timestamp,
        'content_length': len(cleaned_content),
        'knowledge_base': knowledge_base,
        'quality_analysis': quality_stats
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 结果已保存到: {output_file}")
    
    # 总结
    print(f"\n🎯 测试总结:")
    print(f"  - 概念提取: {quality_stats['concepts_count']} 个")
    print(f"  - 模式提取: {quality_stats['patterns_count']} 个")
    print(f"  - 检查清单: {quality_stats['checklist_count']} 个")
    print(f"  - 检查清单有效率: {quality_stats['valid_checklist_ratio']*100:.1f}%")

if __name__ == "__main__":
    main()