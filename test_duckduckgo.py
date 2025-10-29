#!/usr/bin/env python3
"""
测试DuckDuckGo搜索功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from duckduckgo_search import DDGS

def test_duckduckgo_direct():
    """直接测试DuckDuckGo搜索"""
    print("🔍 直接测试DuckDuckGo搜索")
    print("=" * 50)
    
    try:
        ddgs = DDGS()
        results = list(ddgs.text("Python tutorial", max_results=3))
        
        print(f"✅ 搜索成功，找到 {len(results)} 个结果")
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.get('title', 'No title')}")
            print(f"   URL: {result.get('href', 'No URL')}")
            print(f"   摘要: {result.get('body', 'No body')[:100]}...")
            
    except Exception as e:
        print(f"❌ DuckDuckGo搜索失败: {e}")
        import traceback
        traceback.print_exc()

def test_crawler_framework():
    """测试爬虫框架"""
    print("\n🔧 测试爬虫框架")
    print("=" * 50)
    
    try:
        from utils.crawler_framework import CrawlerFramework
        
        crawler = CrawlerFramework()
        print(f"✅ 爬虫框架初始化成功")
        print(f"📊 可用搜索引擎: {list(crawler.engine_configs.keys())}")
        
        # 测试原始数据获取
        raw_result = crawler.fetch_raw_data("duckduckgo", "Python tutorial", max_results=3)
        print(f"📈 原始数据获取: {'✅ 成功' if raw_result.get('success') else '❌ 失败'}")
        
        if raw_result.get('success'):
            raw_data = raw_result.get('raw_data', {})
            results = raw_data.get('results', [])
            print(f"🔍 找到结果数: {len(results)}")
        else:
            print(f"❌ 错误: {raw_result.get('error')}")
            
    except Exception as e:
        print(f"❌ 爬虫框架测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_duckduckgo_direct()
    test_crawler_framework()