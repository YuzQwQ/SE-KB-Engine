#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MCP服务器中集成的爬虫工具功能

这个脚本用于测试新添加到server.py中的crawl_webpage_direct工具函数
"""

import asyncio
import json
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import crawl_webpage_direct

async def test_crawl_webpage_direct():
    """
    测试crawl_webpage_direct函数
    """
    print("=" * 60)
    print("测试MCP服务器集成的爬虫工具功能")
    print("=" * 60)
    
    # 测试URL（使用一个稳定的测试网站）
    test_url = "https://example.com"
    
    print(f"\n🔍 测试URL: {test_url}")
    print("\n⏳ 开始爬取...")
    
    try:
        # 调用MCP工具函数
        result = await crawl_webpage_direct(test_url, save_content=True)
        
        # 解析结果
        result_data = json.loads(result)
        
        print("\n✅ 爬取完成！")
        print("\n📊 爬取结果:")
        print(f"状态: {result_data.get('status')}")
        
        if result_data.get('status') == 'success':
            print(f"标题: {result_data.get('title')}")
            print(f"作者: {result_data.get('author')}")
            print(f"发布时间: {result_data.get('publish_time')}")
            print(f"字数: {result_data.get('word_count')}")
            print(f"标签: {', '.join(result_data.get('tags', []))}")
            print(f"内容长度: {result_data.get('full_content_length')} 字符")
            print(f"原始数据大小: {result_data.get('raw_data_size')} 字符")
            print(f"爬取时间: {result_data.get('crawl_time')}")
            
            # 显示内容预览
            content_preview = result_data.get('content_preview', '')
            if content_preview:
                print(f"\n📄 内容预览:")
                print(content_preview)
            
            # 显示保存的文件信息
            if result_data.get('files_saved'):
                print(f"\n💾 保存的文件:")
                files_saved = result_data['files_saved']
                if files_saved.get('raw_data'):
                    print(f"原始数据: {files_saved['raw_data']}")
                if files_saved.get('parsed_data'):
                    print(f"解析数据: {files_saved['parsed_data']}")
        else:
            print(f"❌ 爬取失败: {result_data.get('error')}")
            suggestions = result_data.get('suggestions', [])
            if suggestions:
                print("\n💡 建议:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        print(f"\n详细错误信息:")
        traceback.print_exc()

async def test_simple_webpage():
    """
    测试简单网页爬取
    """
    print("\n" + "=" * 60)
    print("测试简单网页爬取")
    print("=" * 60)
    
    # 测试一个简单的网页
    simple_url = "https://httpbin.org/html"
    print(f"\n🔍 测试简单URL: {simple_url}")
    
    try:
        result = await crawl_webpage_direct(simple_url, save_content=False)
        result_data = json.loads(result)
        
        print(f"\n状态: {result_data.get('status')}")
        if result_data.get('status') == 'success':
            print(f"标题: {result_data.get('title')}")
            print(f"内容长度: {result_data.get('full_content_length')} 字符")
            print("✅ 简单网页爬取成功")
        else:
            print(f"❌ 爬取失败: {result_data.get('error')}")
        
    except Exception as e:
        print(f"❌ 简单网页测试失败: {str(e)}")

async def test_error_handling():
    """
    测试错误处理机制
    """
    print("\n" + "=" * 60)
    print("测试错误处理机制")
    print("=" * 60)
    
    # 测试无效URL
    invalid_url = "https://invalid-url-that-does-not-exist-12345.com/test"
    print(f"\n🔍 测试无效URL: {invalid_url}")
    
    try:
        result = await crawl_webpage_direct(invalid_url, save_content=False)
        result_data = json.loads(result)
        
        print(f"\n状态: {result_data.get('status')}")
        if result_data.get('status') == 'error':
            print(f"错误信息: {result_data.get('error')}")
            suggestions = result_data.get('suggestions', [])
            if suggestions:
                print("建议:")
                for suggestion in suggestions:
                    print(f"  - {suggestion}")
            print("✅ 错误处理正常")
        else:
            print("⚠️ 预期应该返回错误状态")
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {str(e)}")

async def main():
    """
    主测试函数
    """
    print("开始测试MCP服务器集成的爬虫工具...")
    
    # 测试简单网页
    await test_simple_webpage()
    
    # 测试CSDN文章爬取
    await test_crawl_webpage_direct()
    
    # 测试错误处理
    await test_error_handling()
    
    print("\n🎉 所有测试完成！")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())