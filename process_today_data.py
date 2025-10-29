#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门处理今天17点的数据文件
"""

import json
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append('scripts')

from scripts.universal_knowledge_processor import UniversalKnowledgeProcessor

def process_today_data():
    """处理今天17点的数据"""
    
    # 初始化处理器
    processor = UniversalKnowledgeProcessor()
    print("✅ 初始化通用知识处理器成功")
    
    # 今天17点的数据文件
    data_file = Path("data/raw/DFD设计概念和原则_20251029_165601/google_DFD设计概念和原则_20251029_165601.json")
    
    if not data_file.exists():
        print(f"❌ 数据文件不存在: {data_file}")
        return
    
    print(f"📁 处理文件: {data_file}")
    
    try:
        # 读取JSON文件
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 文件读取成功，数据大小: {len(str(data))} 字符")
        
        # 提取内容
        content = ""
        if 'raw_data' in data and 'organic_results' in data['raw_data']:
            for result in data['raw_data']['organic_results']:
                if 'snippet' in result:
                    content += result['snippet'] + "\n"
                if 'title' in result:
                    content += result['title'] + "\n"
        
        if not content.strip():
            print("⚠️ 未找到有效内容")
            return
        
        print(f"📝 提取内容长度: {len(content)} 字符")
        print(f"📝 内容预览: {content[:200]}...")
        
        # 使用通用知识处理器提取知识
        knowledge_base = processor.extract_knowledge(
            content=content,
            url="https://google.com/search",
            title="DFD设计概念和原则",
            requirement_type="需求分析",
            target_conversion_type="DFD图"
        )
        
        if not knowledge_base:
            print("❌ 未提取到有效知识")
            return
        
        print("✅ 知识提取成功")
        
        # 检查知识库内容
        has_content = False
        for section in ['generation_knowledge', 'validation_knowledge', 'examples']:
            if section in knowledge_base:
                section_data = knowledge_base[section]
                if isinstance(section_data, dict):
                    for key, value in section_data.items():
                        if isinstance(value, list) and len(value) > 0:
                            print(f"📋 {section}.{key}: {len(value)} 项")
                            has_content = True
        
        if not has_content:
            print("⚠️ 知识库内容为空")
        
        # 保存知识库
        result = processor.save_knowledge_base(knowledge_base=knowledge_base)
        print(f"💾 保存结果: {result}")
        
        # 检查保存的文件
        kb_dir = Path("scripts/shared_data/knowledge_base")
        if kb_dir.exists():
            kb_files = list(kb_dir.glob("*20251029*.json"))
            print(f"📁 今天生成的知识库文件数量: {len(kb_files)}")
            for kb_file in kb_files:
                print(f"  📄 {kb_file.name}")
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    process_today_data()