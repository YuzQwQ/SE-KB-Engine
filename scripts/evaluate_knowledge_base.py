#!/usr/bin/env python3
"""
知识库评估脚本
分析当前知识库的数据量、质量和内容分布
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import re

def analyze_knowledge_base():
    """分析知识库"""
    kb_dir = Path("shared_data/knowledge_base")
    
    if not kb_dir.exists():
        print("❌ 知识库目录不存在")
        return
    
    # 统计信息
    stats = {
        'total_files': 0,
        'total_size_mb': 0,
        'sources': defaultdict(int),
        'topics': defaultdict(int),
        'dates': defaultdict(int),
        'reliability_scores': [],
        'concepts_count': [],
        'rules_count': [],
        'examples_count': []
    }
    
    print("🔍 正在分析知识库...")
    
    # 遍历所有JSON文件
    for json_file in kb_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stats['total_files'] += 1
            stats['total_size_mb'] += json_file.stat().st_size / (1024 * 1024)
            
            # 分析元数据
            metadata = data.get('metadata', {})
            source_info = metadata.get('source_info', {})
            
            # 来源分析
            source_url = source_info.get('source_url', '')
            if source_url:
                domain = re.findall(r'https?://([^/]+)', source_url)
                if domain:
                    stats['sources'][domain[0]] += 1
            
            # 主题分析
            title = metadata.get('title', '')
            if 'DFD' in title or '数据流图' in title:
                stats['topics']['DFD数据流图'] += 1
            elif '需求分析' in title:
                stats['topics']['需求分析'] += 1
            elif '软件工程' in title:
                stats['topics']['软件工程'] += 1
            elif 'UML' in title:
                stats['topics']['UML建模'] += 1
            else:
                stats['topics']['其他'] += 1
            
            # 日期分析
            created_time = metadata.get('created_time', '')
            if created_time:
                date = created_time[:10]  # YYYY-MM-DD
                stats['dates'][date] += 1
            
            # 可靠性分析
            reliability = source_info.get('reliability_score', 0)
            stats['reliability_scores'].append(reliability)
            
            # 内容分析
            generation_knowledge = data.get('generation_knowledge', {})
            concepts = generation_knowledge.get('concepts', [])
            rules = generation_knowledge.get('rules', [])
            examples = generation_knowledge.get('examples', [])
            
            stats['concepts_count'].append(len(concepts))
            stats['rules_count'].append(len(rules))
            stats['examples_count'].append(len(examples))
            
        except Exception as e:
            print(f"⚠️ 处理文件 {json_file.name} 时出错: {e}")
    
    # 生成报告
    print_analysis_report(stats)

def print_analysis_report(stats):
    """打印分析报告"""
    print("\n" + "="*60)
    print("📊 知识库评估报告")
    print("="*60)
    
    # 基本统计
    print(f"\n📈 基本统计:")
    print(f"  总文件数: {stats['total_files']}")
    print(f"  总大小: {stats['total_size_mb']:.2f} MB")
    print(f"  平均文件大小: {stats['total_size_mb']/max(stats['total_files'], 1):.2f} MB")
    
    # 来源分析
    print(f"\n🌐 数据来源分布 (前10个):")
    for source, count in Counter(stats['sources']).most_common(10):
        percentage = (count / stats['total_files']) * 100
        print(f"  {source}: {count} 文件 ({percentage:.1f}%)")
    
    # 主题分析
    print(f"\n📚 主题分布:")
    for topic, count in Counter(stats['topics']).most_common():
        percentage = (count / stats['total_files']) * 100
        print(f"  {topic}: {count} 文件 ({percentage:.1f}%)")
    
    # 时间分析
    print(f"\n📅 创建时间分布 (最近10天):")
    for date, count in Counter(stats['dates']).most_common(10):
        print(f"  {date}: {count} 文件")
    
    # 质量分析
    if stats['reliability_scores']:
        avg_reliability = sum(stats['reliability_scores']) / len(stats['reliability_scores'])
        print(f"\n⭐ 质量评估:")
        print(f"  平均可靠性评分: {avg_reliability:.3f}")
        print(f"  高质量文件 (>0.9): {sum(1 for s in stats['reliability_scores'] if s > 0.9)} 个")
        print(f"  中等质量文件 (0.7-0.9): {sum(1 for s in stats['reliability_scores'] if 0.7 <= s <= 0.9)} 个")
        print(f"  低质量文件 (<0.7): {sum(1 for s in stats['reliability_scores'] if s < 0.7)} 个")
    
    # 内容丰富度分析
    if stats['concepts_count']:
        avg_concepts = sum(stats['concepts_count']) / len(stats['concepts_count'])
        avg_rules = sum(stats['rules_count']) / len(stats['rules_count'])
        avg_examples = sum(stats['examples_count']) / len(stats['examples_count'])
        
        print(f"\n📖 内容丰富度:")
        print(f"  平均概念数: {avg_concepts:.1f}")
        print(f"  平均规则数: {avg_rules:.1f}")
        print(f"  平均示例数: {avg_examples:.1f}")
        print(f"  内容丰富的文件 (>10个概念): {sum(1 for c in stats['concepts_count'] if c > 10)} 个")
    
    # 改进建议
    print(f"\n💡 改进建议:")
    
    # 来源多样性建议
    unique_sources = len(stats['sources'])
    if unique_sources < 5:
        print(f"  🔍 扩展数据来源: 当前仅有 {unique_sources} 个来源，建议增加更多权威网站")
    
    # 主题覆盖建议
    dfd_files = stats['topics'].get('DFD数据流图', 0)
    total_files = stats['total_files']
    if dfd_files / total_files < 0.5:
        print(f"  📊 增加DFD相关内容: DFD文件占比仅 {(dfd_files/total_files)*100:.1f}%")
    
    # 质量改进建议
    if stats['reliability_scores']:
        low_quality = sum(1 for s in stats['reliability_scores'] if s < 0.7)
        if low_quality > 0:
            print(f"  ⚡ 提升内容质量: {low_quality} 个文件质量较低，需要重新处理")
    
    # 内容深度建议
    if stats['concepts_count']:
        shallow_files = sum(1 for c in stats['concepts_count'] if c < 5)
        if shallow_files > total_files * 0.3:
            print(f"  📚 深化内容提取: {shallow_files} 个文件内容较浅，建议优化提取算法")
    
    print(f"\n📋 目录结构建议:")
    print(f"  建议按以下结构重新组织:")
    print(f"  📁 shared_data/")
    print(f"    📁 knowledge_base/")
    print(f"      📁 dfd_modeling/        # DFD建模相关")
    print(f"      📁 requirement_analysis/ # 需求分析相关")
    print(f"      📁 software_engineering/ # 软件工程通用")
    print(f"      📁 uml_modeling/        # UML建模相关")
    print(f"      📁 case_studies/        # 案例研究")
    print(f"      📁 archived/            # 低质量或重复内容")

if __name__ == "__main__":
    analyze_knowledge_base()