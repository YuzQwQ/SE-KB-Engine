#!/usr/bin/env python3
"""
调试增强后的search_and_parse_universal工具
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from server import search_and_parse_universal, get_available_search_engines

async def debug_search_engines():
    """调试搜索引擎配置"""
    print("🔍 调试搜索引擎配置")
    print("=" * 60)
    
    try:
        # 获取可用搜索引擎
        engines_result = get_available_search_engines()
        engines_data = json.loads(engines_result)
        
        print(f"📊 搜索引擎配置状态: {engines_data.get('status', 'unknown')}")
        print(f"📈 可用引擎数量: {len(engines_data.get('engines', []))}")
        
        if engines_data.get('engines'):
            print("\n🔧 可用搜索引擎:")
            for engine in engines_data['engines']:
                print(f"  - {engine.get('name', 'unknown')}: {engine.get('status', 'unknown')}")
        else:
            print("❌ 没有找到可用的搜索引擎配置")
            
        return engines_data.get('engines', [])
        
    except Exception as e:
        print(f"❌ 获取搜索引擎配置失败: {e}")
        traceback.print_exc()
        return []

async def debug_basic_search():
    """调试基础搜索功能"""
    print("\n🔍 调试基础搜索功能")
    print("=" * 60)
    
    try:
        # 测试基础搜索
        result = await search_and_parse_universal(
            engine="duckduckgo",
            keyword="Python tutorial",
            max_results=3,
            extract_content=False
        )
        
        data = json.loads(result)
        print(f"📊 搜索状态: {data.get('status', 'unknown')}")
        print(f"🔍 搜索引擎: {data.get('search_engine', 'unknown')}")
        print(f"📈 结果数量: {len(data.get('search_results', []))}")
        
        if data.get('search_results'):
            print("\n📋 搜索结果:")
            for i, result in enumerate(data['search_results'][:3], 1):
                print(f"  {i}. {result.get('title', 'No title')}")
                print(f"     URL: {result.get('url', 'No URL')}")
                print(f"     摘要: {result.get('snippet', 'No snippet')[:100]}...")
        else:
            print("❌ 没有找到搜索结果")
            if 'error' in data:
                print(f"错误信息: {data['error']}")
                
        return data
        
    except Exception as e:
        print(f"❌ 基础搜索测试失败: {e}")
        traceback.print_exc()
        return None

async def debug_search_with_extraction():
    """调试搜索和内容提取功能"""
    print("\n🔍 调试搜索和内容提取功能")
    print("=" * 60)
    
    try:
        # 测试搜索和内容提取
        result = await search_and_parse_universal(
            engine="duckduckgo",
            keyword="Python programming basics",
            max_results=2,
            extract_content=True,
            requirement_type="tutorial",
            target_conversion_type="knowledge_base"
        )
        
        data = json.loads(result)
        print(f"📊 搜索状态: {data.get('status', 'unknown')}")
        print(f"🔍 搜索引擎: {data.get('search_engine', 'unknown')}")
        print(f"📈 搜索结果数量: {len(data.get('search_results', []))}")
        
        # 检查内容提取结果
        extraction = data.get('content_extraction', {})
        if extraction:
            print(f"📚 内容提取状态: {extraction.get('status', 'unknown')}")
            print(f"🔗 处理URL数量: {extraction.get('total_urls_processed', 0)}")
            print(f"✅ 成功提取: {extraction.get('successful_extractions', 0)}")
            print(f"❌ 提取失败: {extraction.get('failed_extractions', 0)}")
            
            if extraction.get('knowledge_bases'):
                print(f"📖 生成知识库数量: {len(extraction['knowledge_bases'])}")
                for kb in extraction['knowledge_bases'][:2]:
                    print(f"  - 文件: {kb.get('file_path', 'unknown')}")
                    print(f"    来源: {kb.get('source_url', 'unknown')}")
        else:
            print("❌ 没有内容提取结果")
            
        return data
        
    except Exception as e:
        print(f"❌ 搜索和提取测试失败: {e}")
        traceback.print_exc()
        return None

async def main():
    """主测试函数"""
    print("🚀 开始调试增强后的search_and_parse_universal工具")
    print("=" * 80)
    
    # 1. 调试搜索引擎配置
    engines = await debug_search_engines()
    
    # 2. 调试基础搜索
    search_result = await debug_basic_search()
    
    # 3. 调试搜索和内容提取
    extraction_result = await debug_search_with_extraction()
    
    print("\n" + "=" * 80)
    print("🎯 调试总结:")
    print(f"  - 搜索引擎配置: {'✅ 正常' if engines else '❌ 异常'}")
    print(f"  - 基础搜索功能: {'✅ 正常' if search_result and search_result.get('status') == 'success' else '❌ 异常'}")
    print(f"  - 内容提取功能: {'✅ 正常' if extraction_result and extraction_result.get('status') == 'success' else '❌ 异常'}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())