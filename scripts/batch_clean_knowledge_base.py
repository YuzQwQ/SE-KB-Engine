#!/usr/bin/env python3
"""
批量清理知识库文件中的HTML标签和实体编码

该脚本会扫描指定目录下的所有JSON知识库文件，
清理其中的HTML标签和HTML实体编码，并生成清理报告。

使用方法:
    python scripts/batch_clean_knowledge_base.py [--directory DIR] [--backup] [--dry-run]

参数:
    --directory DIR: 指定要清理的目录 (默认: shared_data/knowledge_base)
    --backup: 在清理前创建备份文件
    --dry-run: 只显示会被清理的内容，不实际修改文件
    --verbose: 显示详细的清理过程
"""

import os
import sys
import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.html_cleaner import HTMLCleaner, clean_html_content, is_html_content


class KnowledgeBaseCleaner:
    """知识库批量清理器"""
    
    def __init__(self, backup=False, dry_run=False, verbose=False):
        self.backup = backup
        self.dry_run = dry_run
        self.verbose = verbose
        self.cleaner = HTMLCleaner()
        self.stats = {
            'files_processed': 0,
            'files_cleaned': 0,
            'concepts_cleaned': 0,
            'transformations_cleaned': 0,
            'total_html_tags_removed': 0,
            'total_html_entities_removed': 0,
            'errors': []
        }
    
    def clean_text_field(self, text, field_name=""):
        """清理文本字段中的HTML内容"""
        if not isinstance(text, str) or not text.strip():
            return text, False
        
        if not is_html_content(text):
            return text, False
        
        cleaned_text = clean_html_content(text)
        if cleaned_text != text:
            if self.verbose:
                print(f"    清理字段 {field_name}:")
                print(f"      原始: {repr(text[:100])}{'...' if len(text) > 100 else ''}")
                print(f"      清理: {repr(cleaned_text[:100])}{'...' if len(cleaned_text) > 100 else ''}")
            
            # 更新统计信息
            stats = self.cleaner.get_cleaning_stats(text, cleaned_text)
            self.stats['total_html_tags_removed'] += stats['html_tags_removed']
            self.stats['total_html_entities_removed'] += stats['html_entities_removed']
            
            return cleaned_text, True
        
        return text, False
    
    def clean_concept(self, concept):
        """清理概念对象"""
        cleaned = False
        
        if isinstance(concept, dict):
            # 清理定义字段
            if 'definition' in concept:
                concept['definition'], def_cleaned = self.clean_text_field(
                    concept['definition'], 'definition'
                )
                cleaned = cleaned or def_cleaned
            
            # 清理描述字段
            if 'description' in concept:
                concept['description'], desc_cleaned = self.clean_text_field(
                    concept['description'], 'description'
                )
                cleaned = cleaned or desc_cleaned
            
            # 清理其他可能的文本字段
            for field in ['name', 'title', 'content']:
                if field in concept:
                    concept[field], field_cleaned = self.clean_text_field(
                        concept[field], field
                    )
                    cleaned = cleaned or field_cleaned
        
        return cleaned
    
    def clean_transformation(self, transformation):
        """清理转换对象"""
        cleaned = False
        
        if isinstance(transformation, dict):
            # 清理描述字段
            if 'description' in transformation:
                transformation['description'], desc_cleaned = self.clean_text_field(
                    transformation['description'], 'transformation.description'
                )
                cleaned = cleaned or desc_cleaned
            
            # 清理步骤
            if 'steps' in transformation and isinstance(transformation['steps'], list):
                for i, step in enumerate(transformation['steps']):
                    if isinstance(step, dict):
                        # 步骤是字典，清理其中的文本字段
                        for field in ['description', 'action', 'content']:
                            if field in step:
                                step[field], step_cleaned = self.clean_text_field(
                                    step[field], f'step[{i}].{field}'
                                )
                                cleaned = cleaned or step_cleaned
                    elif isinstance(step, str):
                        # 步骤是字符串，直接清理
                        transformation['steps'][i], step_cleaned = self.clean_text_field(
                            step, f'step[{i}]'
                        )
                        cleaned = cleaned or step_cleaned
        
        return cleaned
    
    def clean_json_recursively(self, obj, path=""):
        """递归清理JSON对象中的所有HTML内容"""
        cleaned = False
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, str):
                    # 检查并清理字符串字段
                    if is_html_content(value):
                        cleaned_value, field_cleaned = self.clean_text_field(value, current_path)
                        if field_cleaned:
                            obj[key] = cleaned_value
                            cleaned = True
                            if self.verbose:
                                print(f"  清理了字段: {current_path}")
                else:
                    # 递归处理嵌套对象
                    if self.clean_json_recursively(value, current_path):
                        cleaned = True
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                if isinstance(item, str):
                    # 检查并清理字符串元素
                    if is_html_content(item):
                        cleaned_value, field_cleaned = self.clean_text_field(item, current_path)
                        if field_cleaned:
                            obj[i] = cleaned_value
                            cleaned = True
                            if self.verbose:
                                print(f"  清理了数组元素: {current_path}")
                else:
                    # 递归处理嵌套对象
                    if self.clean_json_recursively(item, current_path):
                        cleaned = True
        
        return cleaned

    def clean_knowledge_file(self, file_path):
        """清理单个知识库文件"""
        try:
            if self.verbose:
                print(f"\n处理文件: {file_path}")
            
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 递归清理整个JSON文件
            file_cleaned = self.clean_json_recursively(data)
            
            # 更新统计信息
            self.stats['files_processed'] += 1
            if file_cleaned:
                self.stats['files_cleaned'] += 1
                
                if not self.dry_run:
                    # 创建备份
                    if self.backup:
                        backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2(file_path, backup_path)
                        if self.verbose:
                            print(f"  创建备份: {backup_path}")
                    
                    # 保存清理后的文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    if self.verbose:
                        print(f"  文件已更新")
                else:
                    if self.verbose:
                        print(f"  [DRY RUN] 文件将被更新")
            else:
                if self.verbose:
                    print(f"  文件无需清理")
            
            return True
            
        except Exception as e:
            error_msg = f"处理文件 {file_path} 时出错: {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"错误: {error_msg}")
            return False
    
    def clean_directory(self, directory):
        """清理目录下的所有知识库文件"""
        directory = Path(directory)
        
        if not directory.exists():
            print(f"错误: 目录不存在 {directory}")
            return False
        
        # 查找所有JSON文件
        json_files = list(directory.rglob("*.json"))
        
        if not json_files:
            print(f"在目录 {directory} 中未找到JSON文件")
            return False
        
        print(f"找到 {len(json_files)} 个JSON文件")
        
        if self.dry_run:
            print("=== DRY RUN 模式 - 不会实际修改文件 ===")
        
        # 处理每个文件
        for file_path in json_files:
            self.clean_knowledge_file(file_path)
        
        return True
    
    def print_summary(self):
        """打印清理摘要"""
        print("\n" + "="*60)
        print("清理摘要:")
        print("="*60)
        print(f"处理文件数: {self.stats['files_processed']}")
        print(f"清理文件数: {self.stats['files_cleaned']}")
        print(f"移除HTML标签数: {self.stats['total_html_tags_removed']}")
        print(f"解码HTML实体数: {self.stats['total_html_entities_removed']}")
        
        if self.stats['errors']:
            print(f"\n错误数: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                print(f"  - {error}")
        
        if self.dry_run:
            print("\n注意: 这是DRY RUN模式，未实际修改任何文件")


def main():
    parser = argparse.ArgumentParser(
        description="批量清理知识库文件中的HTML标签和实体编码",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 清理默认目录
    python scripts/batch_clean_knowledge_base.py
    
    # 清理指定目录并创建备份
    python scripts/batch_clean_knowledge_base.py --directory /path/to/kb --backup
    
    # 预览清理效果（不实际修改文件）
    python scripts/batch_clean_knowledge_base.py --dry-run --verbose
        """
    )
    
    parser.add_argument(
        '--directory', '-d',
        default='shared_data/knowledge_base',
        help='要清理的目录路径 (默认: shared_data/knowledge_base)'
    )
    
    parser.add_argument(
        '--backup', '-b',
        action='store_true',
        help='在清理前创建备份文件'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只显示会被清理的内容，不实际修改文件'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细的清理过程'
    )
    
    args = parser.parse_args()
    
    # 创建清理器
    cleaner = KnowledgeBaseCleaner(
        backup=args.backup,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    # 执行清理
    success = cleaner.clean_directory(args.directory)
    
    # 打印摘要
    cleaner.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())