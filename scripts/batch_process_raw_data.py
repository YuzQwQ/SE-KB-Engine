#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理原始爬取数据到知识库
"""

import json
import os
import sys
import glob
from pathlib import Path

sys.path.append('.')
from server import save_to_knowledge_base
from scripts.format_processor import FormatProcessor

def process_json_file(file_path, processor):
    """
    处理单个JSON文件
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取文件名作为主题
        file_name = Path(file_path).stem
        topic = file_name.replace('_parsed', '').replace('google_', '')
        
        # 根据数据结构提取内容
        content = ""
        source_url = ""
        
        if isinstance(data, dict):
            if 'results' in data:  # Google搜索结果格式
                content = '\n'.join([f"{result.get('title', '')}: {result.get('snippet', '')}" for result in data['results']])
                source_url = data.get('search_url', 'unknown')
            elif 'content' in data:  # 解析后的内容格式
                content = data['content']
                source_url = data.get('url', 'unknown')
            elif 'title' in data and 'snippet' in data:  # 单个搜索结果格式
                content = f"{data['title']}: {data['snippet']}"
                source_url = data.get('url', 'unknown')
            else:
                # 尝试提取所有文本内容
                content = str(data)
                source_url = 'unknown'
        elif isinstance(data, list):
            # 处理列表格式的数据
            content = '\n'.join([str(item) for item in data])
            source_url = 'unknown'
        else:
            content = str(data)
            source_url = 'unknown'
        
        if not content.strip():
            print(f"⚠️  文件 {file_path} 内容为空，跳过处理")
            return None
        
        print(f"📄 处理文件: {file_name}")
        print(f"📝 内容长度: {len(content)} 字符")
        
        # 使用通用知识处理器提取知识
        extracted_data = processor.extract_knowledge(content, source_url, topic)
        
        if not extracted_data:
            print(f"⚠️  文件 {file_path} 未提取到有效知识，跳过")
            return None
        
        # 生成JSON结构
        json_obj = processor.generate_json_structure(extracted_data, source_url, topic)
        
        # 保存到知识库
        result = save_to_knowledge_base(json.dumps(json_obj, ensure_ascii=False), topic)
        
        print(f"💾 保存结果: {result}")
        print(f"✅ 成功处理文件: {file_name}")
        return result
        
    except Exception as e:
        print(f"❌ 处理文件 {file_path} 时出错: {e}")
        return None

def main():
    """
    批量处理所有原始数据文件
    """
    try:
        # 初始化格式处理器
        processor = FormatProcessor(format_type="dfd")
        print(f"✅ 初始化格式处理器: {processor.get_format_name()}")
        
        # 查找所有原始数据文件
        raw_data_dir = 'data/raw'
        
        # 查找所有JSON文件
        json_files = []
        
        # 查找根目录下的JSON文件
        root_json_files = glob.glob(os.path.join(raw_data_dir, '*.json'))
        json_files.extend(root_json_files)
        
        # 查找子目录中的JSON文件
        subdirs = [d for d in os.listdir(raw_data_dir) if os.path.isdir(os.path.join(raw_data_dir, d))]
        for subdir in subdirs:
            subdir_json_files = glob.glob(os.path.join(raw_data_dir, subdir, '*.json'))
            json_files.extend(subdir_json_files)
        
        print(f"📊 找到 {len(json_files)} 个JSON文件待处理")
        
        if not json_files:
            print("⚠️  未找到任何JSON文件")
            return
        
        # 处理每个文件（测试模式：只处理前1个文件）
        success_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(json_files, 1):  # 处理所有文件
            print(f"\n🔄 处理进度: {i}/{len(json_files)}")
            print(f"📁 文件路径: {file_path}")
            
            result = process_json_file(file_path, processor)
            
            if result:
                success_count += 1
            else:
                failed_count += 1
        
        print(f"\n📈 处理完成统计:")
        print(f"✅ 成功处理: {success_count} 个文件")
        print(f"❌ 处理失败: {failed_count} 个文件")
        print(f"📊 总计文件: {len(json_files)} 个")
        
        # 检查生成的知识库文件
        knowledge_base_dir = 'shared_data/knowledge_base'
        if os.path.exists(knowledge_base_dir):
            kb_files = glob.glob(os.path.join(knowledge_base_dir, '*.json'))
            print(f"\n📚 知识库文件数量: {len(kb_files)}")
            for kb_file in kb_files:
                print(f"  📄 {os.path.basename(kb_file)}")
        
    except Exception as e:
        print(f"❌ 批量处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()