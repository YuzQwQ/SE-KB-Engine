#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试网页爬取和HTML标题结构功能
使用MCP工具直接爬取网页
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from utils.html_cleaner import clean_html_with_structure, is_html_content, html_cleaner

class DirectScrapeTest:
    def __init__(self):
        self.session = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self):
        """连接到MCP服务器"""
        server_params = StdioServerParameters(
            command="python",
            args=["server.py"],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

        await self.session.initialize()
        response = await self.session.list_tools()
        print(f"✅ 已连接到MCP服务器，可用工具: {[tool.name for tool in response.tools]}")
        return True

    async def scrape_webpage(self, url):
        """爬取网页"""
        print(f"\n=== 爬取网页: {url} ===")
        
        try:
            result = await self.session.call_tool("scrape_webpage", {"url": url})
            
            if result.isError:
                print(f"✗ 爬取失败: {result.content}")
                return None
            
            # 解析结果
            content = result.content[0].text if result.content else ""
            
            # 尝试解析为JSON
            try:
                # 首先尝试直接解析
                data = json.loads(content)
                
                # 检查是否有嵌套的JSON字符串
                if isinstance(data.get('content'), str):
                    try:
                        # 尝试解析嵌套的JSON
                        nested_content = data['content']
                        # 移除警告信息，只保留JSON部分
                        if '{\n  "status"' in nested_content:
                            json_start = nested_content.find('{\n  "status"')
                            json_content = nested_content[json_start:]
                            nested_data = json.loads(json_content)
                            
                            print(f"✓ 爬取成功!")
                            print(f"  标题: {nested_data.get('title', '未获取')}")
                            print(f"  作者: {nested_data.get('author', '未获取')}")
                            print(f"  发布时间: {nested_data.get('publish_time', '未获取')}")
                            print(f"  字数: {nested_data.get('word_count', 0)}")
                            print(f"  内容预览长度: {len(nested_data.get('content_preview', ''))}")
                            print(f"  完整内容长度: {nested_data.get('full_content_length', 0)}")
                            
                            # 检查是否有保存的原始数据文件
                            raw_file = nested_data.get('files_saved', {}).get('raw_data')
                            if raw_file:
                                print(f"  原始数据文件: {raw_file}")
                                # 尝试读取原始HTML数据
                                try:
                                    with open(raw_file, 'r', encoding='utf-8') as f:
                                        raw_data = json.load(f)
                                        html_content = raw_data.get('content', '')
                                        if html_content:
                                            print(f"  原始HTML长度: {len(html_content)} 字符")
                                            return {
                                                'content': html_content,
                                                'title': nested_data.get('title', ''),
                                                'url': nested_data.get('url', url),
                                                'metadata': nested_data
                                            }
                                except Exception as e:
                                    print(f"  读取原始数据失败: {e}")
                            
                            # 如果没有原始HTML，使用content_preview
                            return {
                                'content': nested_data.get('content_preview', ''),
                                'title': nested_data.get('title', ''),
                                'url': nested_data.get('url', url),
                                'metadata': nested_data
                            }
                    except json.JSONDecodeError:
                        pass
                
                print(f"✓ 爬取成功!")
                print(f"  标题: {data.get('title', '未获取')}")
                print(f"  URL: {data.get('url', '未获取')}")
                print(f"  内容长度: {len(data.get('content', ''))} 字符")
                
                return data
            except json.JSONDecodeError:
                print(f"✓ 爬取成功 (纯文本)!")
                print(f"  内容长度: {len(content)} 字符")
                return {"content": content, "title": "未解析", "url": url}
                
        except Exception as e:
            print(f"✗ 爬取异常: {e}")
            return None

    async def test_html_structure(self, scrape_result):
        """测试HTML结构处理"""
        if not scrape_result:
            print("没有爬取结果，跳过HTML结构测试")
            return None
        
        print(f"\n=== 测试HTML结构处理 ===")
        
        content = scrape_result.get('content', '')
        
        # 1. 检测HTML内容
        is_html = is_html_content(content)
        print(f"1. HTML内容检测: {'是' if is_html else '否'}")
        
        if not is_html:
            print("   内容不是HTML格式")
            return None
        
        # 2. 结构化清理
        print("2. 进行结构化清理...")
        cleaning_result = clean_html_with_structure(content)
        
        print(f"   原始长度: {len(content)} 字符")
        print(f"   清理后长度: {len(cleaning_result['cleaned_content'])} 字符")
        print(f"   提取标题数: {len(cleaning_result['title_structure'])}")
        
        # 3. 显示标题结构
        if cleaning_result['title_structure']:
            print("3. 提取的标题结构:")
            for i, title in enumerate(cleaning_result['title_structure'][:10], 1):  # 只显示前10个
                print(f"   {i}. [H{title['level']}] {title['text'][:50]}...")
        else:
            print("3. 未提取到标题结构")
        
        # 4. 生成上下文
        if cleaning_result['title_structure']:
            title_context = html_cleaner.format_title_structure_as_context(
                cleaning_result['title_structure']
            )
            print(f"4. 标题上下文生成: {len(title_context)} 字符")
            print("   上下文预览:")
            print(title_context[:200] + "..." if len(title_context) > 200 else title_context)
        else:
            title_context = ""
            print("4. 无标题结构，跳过上下文生成")
        
        # 5. 内容预览
        print("5. 清理后内容预览 (前200字符):")
        print(cleaning_result['cleaned_content'][:200] + "...")
        
        return {
            'original_content': content,
            'cleaned_content': cleaning_result['cleaned_content'],
            'title_structure': cleaning_result['title_structure'],
            'title_context': title_context,
            'is_html': is_html
        }

    async def run_test(self, url):
        """运行完整测试"""
        print("开始直接爬取测试...")
        
        try:
            # 连接服务器
            await self.connect_to_server()
            
            # 爬取网页
            scrape_result = await self.scrape_webpage(url)
            
            # 测试HTML结构处理
            structure_result = await self.test_html_structure(scrape_result)
            
            # 保存结果
            if scrape_result:
                with open('direct_scrape_result.json', 'w', encoding='utf-8') as f:
                    json.dump(scrape_result, f, ensure_ascii=False, indent=2)
                print(f"\n✓ 爬取结果已保存到 direct_scrape_result.json")
            
            if structure_result:
                # 只保存部分数据避免文件过大
                save_data = {
                    'original_length': len(structure_result['original_content']),
                    'cleaned_length': len(structure_result['cleaned_content']),
                    'title_count': len(structure_result['title_structure']),
                    'title_structure': structure_result['title_structure'][:20],  # 只保存前20个标题
                    'title_context': structure_result['title_context'],
                    'cleaned_preview': structure_result['cleaned_content'][:1000],  # 只保存前1000字符
                    'is_html': structure_result['is_html']
                }
                
                with open('direct_structure_result.json', 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                print(f"✓ 结构处理结果已保存到 direct_structure_result.json")
            
            print(f"\n{'='*60}")
            print("=== 测试总结 ===")
            if scrape_result and structure_result:
                print("✓ 网页爬取: 成功")
                print(f"✓ HTML检测: {'通过' if structure_result['is_html'] else '非HTML'}")
                print(f"✓ 标题提取: {len(structure_result['title_structure'])} 个")
                print(f"✓ 内容清理: {len(structure_result['original_content'])} → {len(structure_result['cleaned_content'])} 字符")
                if structure_result['title_context']:
                    print(f"✓ 上下文生成: {len(structure_result['title_context'])} 字符")
                print("\n🎉 所有功能测试通过！")
            else:
                print("✗ 测试未完全通过，请检查错误信息")
                
        except Exception as e:
            print(f"测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.exit_stack.aclose()

async def main():
    """主函数"""
    url = "https://blog.csdn.net/weixin_34640289/article/details/142647843"
    
    test = DirectScrapeTest()
    await test.run_test(url)

if __name__ == "__main__":
    asyncio.run(main())