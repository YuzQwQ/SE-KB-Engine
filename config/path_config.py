#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一路径配置文件
用于管理项目中所有目录路径，避免硬编码路径不一致问题
"""

from pathlib import Path
import os

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录配置
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PARSED_DATA_DIR = DATA_DIR / "parsed"
CONVERTED_DATA_DIR = DATA_DIR / "converted"

# 知识库目录配置
SHARED_DATA_DIR = PROJECT_ROOT / "shared_data"
KNOWLEDGE_BASE_DIR = SHARED_DATA_DIR / "knowledge_base"
ARCHIVED_DIR = KNOWLEDGE_BASE_DIR / "archived"
DFD_MODELING_DIR = KNOWLEDGE_BASE_DIR / "dfd_modeling"
REQUIREMENT_ANALYSIS_DIR = KNOWLEDGE_BASE_DIR / "requirement_analysis"
SOFTWARE_ENGINEERING_DIR = KNOWLEDGE_BASE_DIR / "software_engineering"
UML_MODELING_DIR = KNOWLEDGE_BASE_DIR / "uml_modeling"
CASE_STUDIES_DIR = KNOWLEDGE_BASE_DIR / "case_studies"

# LLM数据目录
JSON_LLM_READY_DIR = SHARED_DATA_DIR / "json_llm_ready"
MARKDOWN_LLM_READY_DIR = SHARED_DATA_DIR / "markdown_llm_ready"

# 日志目录
LOGS_DIR = PROJECT_ROOT / "logs"

# 配置目录
CONFIG_DIR = PROJECT_ROOT / "config"

# 工具目录
UTILS_DIR = PROJECT_ROOT / "utils"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# 测试目录
TESTS_DIR = PROJECT_ROOT / "tests"

# 静态文件目录
STATIC_DIR = PROJECT_ROOT / "static"

def ensure_directories():
    """确保所有必要的目录都存在"""
    directories = [
        DATA_DIR, RAW_DATA_DIR, PARSED_DATA_DIR, CONVERTED_DATA_DIR,
        SHARED_DATA_DIR, KNOWLEDGE_BASE_DIR, ARCHIVED_DIR,
        DFD_MODELING_DIR, REQUIREMENT_ANALYSIS_DIR, SOFTWARE_ENGINEERING_DIR,
        UML_MODELING_DIR, CASE_STUDIES_DIR,
        JSON_LLM_READY_DIR, MARKDOWN_LLM_READY_DIR,
        LOGS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ 确保目录存在: {directory}")

def get_path_config():
    """获取所有路径配置"""
    return {
        'project_root': PROJECT_ROOT,
        'data': {
            'root': DATA_DIR,
            'raw': RAW_DATA_DIR,
            'parsed': PARSED_DATA_DIR,
            'converted': CONVERTED_DATA_DIR
        },
        'shared_data': {
            'root': SHARED_DATA_DIR,
            'knowledge_base': KNOWLEDGE_BASE_DIR,
            'archived': ARCHIVED_DIR,
            'dfd_modeling': DFD_MODELING_DIR,
            'requirement_analysis': REQUIREMENT_ANALYSIS_DIR,
            'software_engineering': SOFTWARE_ENGINEERING_DIR,
            'uml_modeling': UML_MODELING_DIR,
            'case_studies': CASE_STUDIES_DIR,
            'json_llm_ready': JSON_LLM_READY_DIR,
            'markdown_llm_ready': MARKDOWN_LLM_READY_DIR
        },
        'logs': LOGS_DIR,
        'config': CONFIG_DIR,
        'utils': UTILS_DIR,
        'scripts': SCRIPTS_DIR,
        'tests': TESTS_DIR,
        'static': STATIC_DIR
    }

# 路径配置字典，供其他脚本使用
PATHS = get_path_config()

if __name__ == "__main__":
    print("🚀 初始化路径配置...")
    ensure_directories()
    print("✅ 路径配置完成！")
    
    # 打印所有路径
    config = get_path_config()
    for category, paths in config.items():
        if isinstance(paths, dict):
            print(f"\n📁 {category}:")
            for key, path in paths.items():
                print(f"  {key}: {path}")
        else:
            print(f"\n📁 {category}: {paths}")