#!/usr/bin/env python3
"""
知识库重组脚本
按主题和质量重新分类现有知识库文件
"""

import json
import os
import shutil
from pathlib import Path
from collections import defaultdict
import re

def create_directory_structure():
    """创建新的目录结构"""
    base_dir = Path("shared_data/knowledge_base")
    
    # 新的目录结构
    new_dirs = [
        "dfd_modeling",           # DFD建模相关
        "requirement_analysis",   # 需求分析相关
        "software_engineering",   # 软件工程通用
        "uml_modeling",          # UML建模相关
        "case_studies",          # 案例研究
        "archived",              # 低质量或重复内容
        "uncategorized"          # 未分类内容
    ]
    
    for dir_name in new_dirs:
        new_dir = base_dir / dir_name
        new_dir.mkdir(exist_ok=True)
        print(f"✅ 创建目录: {new_dir}")
    
    return new_dirs

def categorize_file(data):
    """根据文件内容确定分类"""
    metadata = data.get('metadata', {})
    title = metadata.get('title', '').lower()
    description = metadata.get('description', '').lower()
    source_url = metadata.get('source_info', {}).get('source_url', '').lower()
    reliability = metadata.get('source_info', {}).get('reliability_score', 0)
    
    # 检查质量
    if reliability < 0.7:
        return 'archived', f'低质量文件 (可靠性: {reliability:.3f})'
    
    # 检查内容丰富度
    concepts_count = len(data.get('generation_knowledge', {}).get('concepts', []))
    if concepts_count < 2:
        return 'archived', f'内容过少 (概念数: {concepts_count})'
    
    # 按主题分类
    content_text = f"{title} {description} {source_url}"
    
    # DFD相关
    if any(keyword in content_text for keyword in [
        'dfd', '数据流图', 'data flow diagram', '数据流程图', 
        '数据流', 'dataflow', '流程图建模'
    ]):
        return 'dfd_modeling', 'DFD建模相关'
    
    # 需求分析相关
    elif any(keyword in content_text for keyword in [
        '需求分析', 'requirement analysis', '需求工程', 'requirement engineering',
        '需求建模', '业务分析', '系统分析'
    ]):
        return 'requirement_analysis', '需求分析相关'
    
    # UML相关
    elif any(keyword in content_text for keyword in [
        'uml', 'unified modeling language', '统一建模语言', 
        '用例图', '类图', '时序图', '活动图'
    ]):
        return 'uml_modeling', 'UML建模相关'
    
    # 软件工程通用
    elif any(keyword in content_text for keyword in [
        '软件工程', 'software engineering', '系统设计', 'system design',
        '软件设计', '架构设计', '设计模式'
    ]):
        return 'software_engineering', '软件工程通用'
    
    # 案例研究
    elif any(keyword in content_text for keyword in [
        '案例', 'case study', '实例', '例子', '实战', '项目',
        '应用', 'application', '实践'
    ]):
        return 'case_studies', '案例研究'
    
    # 默认未分类
    else:
        return 'uncategorized', '未分类内容'

def reorganize_knowledge_base():
    """重组知识库"""
    kb_dir = Path("shared_data/knowledge_base")
    
    if not kb_dir.exists():
        print("❌ 知识库目录不存在")
        return
    
    # 创建新目录结构
    print("📁 创建新的目录结构...")
    new_dirs = create_directory_structure()
    
    # 统计信息
    stats = defaultdict(int)
    moved_files = []
    error_files = []
    
    print("\n🔄 开始重组文件...")
    
    # 遍历所有JSON文件
    json_files = list(kb_dir.glob("*.json"))
    total_files = len(json_files)
    
    for i, json_file in enumerate(json_files, 1):
        try:
            # 读取文件内容
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 确定分类
            category, reason = categorize_file(data)
            
            # 移动文件
            target_dir = kb_dir / category
            target_file = target_dir / json_file.name
            
            # 如果目标文件已存在，添加序号
            counter = 1
            original_target = target_file
            while target_file.exists():
                stem = original_target.stem
                suffix = original_target.suffix
                target_file = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            shutil.move(str(json_file), str(target_file))
            
            stats[category] += 1
            moved_files.append({
                'file': json_file.name,
                'category': category,
                'reason': reason,
                'new_path': str(target_file.relative_to(kb_dir))
            })
            
            # 显示进度
            if i % 50 == 0 or i == total_files:
                print(f"  进度: {i}/{total_files} ({(i/total_files)*100:.1f}%)")
            
        except Exception as e:
            error_files.append({'file': json_file.name, 'error': str(e)})
            print(f"⚠️ 处理文件 {json_file.name} 时出错: {e}")
    
    # 生成重组报告
    print_reorganization_report(stats, moved_files, error_files)
    
    # 保存详细日志
    save_reorganization_log(moved_files, error_files)

def print_reorganization_report(stats, moved_files, error_files):
    """打印重组报告"""
    print("\n" + "="*60)
    print("📊 知识库重组报告")
    print("="*60)
    
    print(f"\n📈 重组统计:")
    total_moved = sum(stats.values())
    print(f"  成功移动文件: {total_moved}")
    print(f"  处理错误文件: {len(error_files)}")
    
    print(f"\n📁 分类分布:")
    category_names = {
        'dfd_modeling': 'DFD建模相关',
        'requirement_analysis': '需求分析相关',
        'software_engineering': '软件工程通用',
        'uml_modeling': 'UML建模相关',
        'case_studies': '案例研究',
        'archived': '已归档(低质量)',
        'uncategorized': '未分类'
    }
    
    for category, count in stats.items():
        name = category_names.get(category, category)
        percentage = (count / total_moved) * 100 if total_moved > 0 else 0
        print(f"  {name}: {count} 文件 ({percentage:.1f}%)")
    
    if error_files:
        print(f"\n❌ 错误文件:")
        for error in error_files[:5]:  # 只显示前5个错误
            print(f"  {error['file']}: {error['error']}")
        if len(error_files) > 5:
            print(f"  ... 还有 {len(error_files) - 5} 个错误文件")
    
    print(f"\n✅ 重组完成!")
    print(f"  新的目录结构位于: shared_data/knowledge_base/")
    print(f"  详细日志保存在: reorganization_log.json")

def save_reorganization_log(moved_files, error_files):
    """保存重组日志"""
    log_data = {
        'timestamp': str(datetime.now()),
        'summary': {
            'total_moved': len(moved_files),
            'total_errors': len(error_files)
        },
        'moved_files': moved_files,
        'error_files': error_files
    }
    
    with open('reorganization_log.json', 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    from datetime import datetime
    reorganize_knowledge_base()