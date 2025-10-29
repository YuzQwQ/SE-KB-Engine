#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动处理10月24日的数据流图相关数据到知识库
"""

import json
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append('.')

from universal_knowledge_processor import UniversalKnowledgeProcessor

def process_october_24_data():
    """处理10月24日的数据"""
    print("🚀 开始处理10月24日的数据流图相关数据...")
    
    # 初始化处理器
    processor = UniversalKnowledgeProcessor()
    print("✅ 初始化通用知识处理器成功")
    
    # 10月24日的数据文件路径
    data_files = [
        "data/raw/数据流图的定义和作用_20251024_095629/google_数据流图的定义和作用_20251024_095629.json",
        "data/raw/数据流图的定义和作用_20251024_100302/google_数据流图的定义和作用_20251024_100302.json"
    ]
    
    processed_count = 0
    
    for file_path in data_files:
        if not os.path.exists(file_path):
            print(f"⚠️  文件不存在: {file_path}")
            continue
            
        print(f"\n📄 处理文件: {file_path}")
        
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取搜索结果内容
            content_parts = []
            
            # 添加答案框内容
            if 'raw_data' in data and 'answer_box' in data['raw_data']:
                answer_box = data['raw_data']['answer_box']
                content_parts.append(f"【答案框】{answer_box.get('title', '')}: {answer_box.get('snippet', '')}")
            
            # 添加有机搜索结果
            if 'raw_data' in data and 'organic_results' in data['raw_data']:
                for i, result in enumerate(data['raw_data']['organic_results'][:10]):  # 取前10个结果
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    content_parts.append(f"【搜索结果{i+1}】{title}: {snippet}")
            
            # 合并内容
            content = '\n'.join(content_parts)
            
            if not content.strip():
                print(f"⚠️  文件 {file_path} 内容为空，跳过处理")
                continue
            
            print(f"📝 提取内容长度: {len(content)} 字符")
            print(f"📝 内容预览: {content[:200]}...")
            
            # 使用通用知识处理器提取知识
            knowledge_base = processor.extract_knowledge(
                content=content,
                url="https://google.com/search?q=数据流图的定义和作用",
                title="数据流图的定义和作用",
                requirement_type="需求分析",
                target_conversion_type="DFD图"
            )
            
            if not knowledge_base:
                print(f"⚠️  文件 {file_path} 未提取到有效知识，跳过")
                continue
            
            # 保存到知识库
            try:
                result_path = processor.save_knowledge_base(
                    knowledge_base=knowledge_base,
                    output_dir="shared_data"  # 直接保存到shared_data目录
                )
                print(f"💾 保存成功: {result_path}")
                processed_count += 1
                
            except Exception as save_error:
                print(f"❌ 保存知识库时出错: {save_error}")
                continue
                
        except Exception as e:
            print(f"❌ 处理文件 {file_path} 时出错: {e}")
            continue
    
    print(f"\n🎯 处理完成!")
    print(f"✅ 成功处理: {processed_count} 个文件")
    
    # 检查生成的知识库文件
    shared_data_dir = Path('shared_data')
    if shared_data_dir.exists():
        kb_files = list(shared_data_dir.glob('universal_kb_*.json'))
        print(f"\n📚 知识库文件数量: {len(kb_files)}")
        for kb_file in kb_files[-5:]:  # 显示最新的5个文件
            print(f"  📄 {kb_file.name}")

if __name__ == "__main__":
    process_october_24_data()