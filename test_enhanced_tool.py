#!/usr/bin/env python3
"""
测试增强后的search_and_parse_universal工具
"""

import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_enhanced_search_tool():
    """测试增强后的search_and_parse_universal工具"""
    
    # 连接到MCP服务器
    server_script_path = Path(__file__).parent / "server.py"
    server_params = StdioServerParameters(
        command="python", args=[str(server_script_path)]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化会话
            await session.initialize()
            
            print("🔧 测试增强后的search_and_parse_universal工具")
            print("=" * 60)
            
            # 测试1: 仅搜索不提取内容
            print("\n📋 测试1: 仅搜索不提取内容")
            print("-" * 40)
            
            try:
                result1 = await session.call_tool(
                    "search_and_parse_universal",
                    {
                        "engine": "duckduckgo",
                        "keyword": "Python编程教程",
                        "max_results": 3,
                        "extract_content": False
                    }
                )
                
                response1 = json.loads(result1.content[0].text)
                print(f"✅ 搜索成功: 找到 {len(response1.get('parsed_response', {}).get('results', []))} 个结果")
                print(f"📊 搜索引擎: {response1.get('summary', {}).get('engine', 'unknown')}")
                print(f"🔍 关键词: {response1.get('summary', {}).get('keyword', 'unknown')}")
                print(f"📈 内容提取: {response1.get('summary', {}).get('extraction_enabled', False)}")
                
            except Exception as e:
                print(f"❌ 测试1失败: {str(e)}")
            
            # 测试2: 搜索并提取内容
            print("\n📋 测试2: 搜索并提取内容")
            print("-" * 40)
            
            try:
                result2 = await session.call_tool(
                    "search_and_parse_universal",
                    {
                        "engine": "duckduckgo",
                        "keyword": "数据流图DFD设计",
                        "max_results": 2,
                        "extract_content": True,
                        "requirement_type": "技术学习",
                        "target_conversion_type": "知识库",
                        "auto_save": False  # 测试时不保存文件
                    }
                )
                
                response2 = json.loads(result2.content[0].text)
                content_extraction = response2.get('content_extraction', {})
                
                print(f"✅ 搜索和提取成功")
                print(f"📊 处理URL总数: {content_extraction.get('total_urls_processed', 0)}")
                print(f"✅ 成功提取: {content_extraction.get('successful_extractions', 0)}")
                print(f"❌ 提取失败: {content_extraction.get('failed_extractions', 0)}")
                print(f"📚 知识库数量: {response2.get('summary', {}).get('total_knowledge_bases', 0)}")
                
                # 显示提取的知识库概要
                extracted_knowledge = content_extraction.get('extracted_knowledge', [])
                for i, kb in enumerate(extracted_knowledge[:2], 1):  # 只显示前2个
                    print(f"\n📖 知识库 {i}:")
                    print(f"   🔗 URL: {kb.get('url', 'unknown')}")
                    print(f"   📝 标题: {kb.get('title', 'unknown')}")
                    knowledge_base = kb.get('knowledge_base', {})
                    metadata = knowledge_base.get('metadata', {})
                    print(f"   🆔 知识库ID: {metadata.get('knowledge_id', 'unknown')}")
                    print(f"   📅 创建时间: {metadata.get('created_time', 'unknown')}")
                
            except Exception as e:
                print(f"❌ 测试2失败: {str(e)}")
            
            # 测试3: 获取可用搜索引擎
            print("\n📋 测试3: 获取可用搜索引擎")
            print("-" * 40)
            
            try:
                result3 = await session.call_tool("get_available_search_engines", {})
                engines_info = json.loads(result3.content[0].text)
                
                print(f"✅ 获取搜索引擎信息成功")
                engines = engines_info.get('engines', [])
                print(f"📊 可用引擎数量: {len(engines)}")
                
                for engine in engines:
                    print(f"   🔍 {engine.get('name', 'unknown')}: {engine.get('description', 'no description')}")
                
            except Exception as e:
                print(f"❌ 测试3失败: {str(e)}")
            
            print("\n" + "=" * 60)
            print("🎉 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_search_tool())