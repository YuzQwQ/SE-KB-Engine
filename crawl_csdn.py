#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSDN文章爬取脚本
用于爬取指定的CSDN文章内容
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.webpage_crawler import WebpageCrawler
import logging

# 设置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    # 目标URL
    target_url = "https://blog.csdn.net/csdnnews/article/details/152307110?spm=1000.2115.3001.5926"
    
    logger.info(f"开始爬取CSDN文章: {target_url}")
    
    try:
        # 创建爬虫实例
        crawler = WebpageCrawler()
        
        # 爬取并解析文章
        result = crawler.crawl_and_parse(target_url, save_data=True)
        
        if result['success']:
            parsed_data = result['parsed_data']
            
            print("\n" + "="*80)
            print("爬取成功！")
            print("="*80)
            print(f"标题: {parsed_data.get('title', 'N/A')}")
            print(f"作者: {parsed_data.get('author', 'N/A')}")
            print(f"发布时间: {parsed_data.get('publish_time', 'N/A')}")
            print(f"字数: {parsed_data.get('word_count', 0)}")
            print(f"标签: {', '.join(parsed_data.get('tags', []))}")
            
            # 显示内容预览（前500字符）
            content = parsed_data.get('content', '')
            if content:
                print("\n内容预览:")
                print("-" * 40)
                print(content[:500] + ("..." if len(content) > 500 else ""))
            
            # 显示保存的文件路径
            if 'file_paths' in result:
                print("\n保存的文件:")
                print(f"原始数据: {result['file_paths']['raw_file']}")
                if result['file_paths']['parsed_file']:
                    print(f"解析数据: {result['file_paths']['parsed_file']}")
                    
        else:
            print("\n爬取失败！")
            print(f"错误信息: {result.get('error', '未知错误')}")
            
            # 如果是原始数据获取失败
            if 'raw_data' in result and not result['raw_data']['success']:
                raw_error = result['raw_data']['error']
                print(f"网络请求错误: {raw_error}")
                
                # 提供一些建议
                if 'timeout' in raw_error.lower():
                    print("\n建议:")
                    print("- 检查网络连接")
                    print("- 尝试增加超时时间")
                    print("- 稍后重试")
                elif 'connection' in raw_error.lower():
                    print("\n建议:")
                    print("- 检查目标网站是否可访问")
                    print("- 检查防火墙设置")
                    print("- 尝试使用VPN")
                    
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        print(f"\n程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        
if __name__ == "__main__":
    main()