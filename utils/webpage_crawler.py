#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页爬虫模块
专门用于爬取网页内容，支持CSDN等网站
"""

import requests
import time
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebpageCrawler:
    """网页爬虫类"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_data_dir = self.data_dir / "raw"
        self.parsed_data_dir = self.data_dir / "parsed"
        
        # 创建必要的目录
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认请求头，模拟真实浏览器
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # 会话对象，保持连接
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_webpage(self, url: str, timeout: int = 120, retry_times: int = 3) -> Dict[str, Any]:
        """获取网页内容
        
        Args:
            url: 目标网址
            timeout: 超时时间（秒）
            retry_times: 重试次数
            
        Returns:
            包含网页内容和元数据的字典
        """
        logger.info(f"开始爬取网页: {url}")
        
        for attempt in range(retry_times):
            try:
                # 添加随机延迟，避免被反爬
                if attempt > 0:
                    delay = min(2 ** attempt, 10)  # 指数退避，最大10秒
                    logger.info(f"第{attempt + 1}次尝试，等待{delay}秒...")
                    time.sleep(delay)
                
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                
                # 检测编码
                if response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding
                
                result = {
                    'url': url,
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content': response.text,
                    'encoding': response.encoding,
                    'timestamp': datetime.now().isoformat(),
                    'success': True,
                    'error': None
                }
                
                logger.info(f"成功获取网页内容，状态码: {response.status_code}")
                return result
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"第{attempt + 1}次尝试失败: {str(e)}")
                if attempt == retry_times - 1:
                    return {
                        'url': url,
                        'status_code': None,
                        'headers': {},
                        'content': '',
                        'encoding': None,
                        'timestamp': datetime.now().isoformat(),
                        'success': False,
                        'error': str(e)
                    }
                    
    def parse_csdn_article(self, html_content: str, url: str) -> Dict[str, Any]:
        """解析CSDN文章内容
        
        Args:
            html_content: HTML内容
            url: 文章URL
            
        Returns:
            解析后的文章数据
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取文章标题
        title = ''
        title_selectors = [
            'h1.title-article',
            '.article-title-box h1',
            'h1',
            '.title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                break
                
        # 提取文章内容
        content = ''
        content_selectors = [
            '#content_views',
            '.article_content',
            '.blog-content-box',
            'article',
            '.content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除不需要的元素
                for unwanted in content_elem.select('script, style, .hljs-button'):
                    unwanted.decompose()
                content = content_elem.get_text().strip()
                break
                
        # 提取作者信息
        author = ''
        author_selectors = [
            '.follow-nickName',
            '.username',
            '.author-name',
            '.user-info .name'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get_text().strip()
                break
                
        # 提取发布时间
        publish_time = ''
        time_selectors = [
            '.time',
            '.publish-time',
            '.article-bar-top .time',
            '.blog-content-box .time'
        ]
        
        for selector in time_selectors:
            time_elem = soup.select_one(selector)
            if time_elem:
                publish_time = time_elem.get_text().strip()
                break
                
        # 提取标签
        tags = []
        tag_selectors = [
            '.tags-box .tag-link',
            '.article-tags a',
            '.tag'
        ]
        
        for selector in tag_selectors:
            tag_elems = soup.select(selector)
            if tag_elems:
                tags = [tag.get_text().strip() for tag in tag_elems]
                break
                
        return {
            'title': title,
            'content': content,
            'author': author,
            'publish_time': publish_time,
            'tags': tags,
            'url': url,
            'word_count': len(content),
            'parsed_at': datetime.now().isoformat()
        }
        
    def save_data(self, data: Dict[str, Any], filename_prefix: str) -> Dict[str, str]:
        """保存数据到文件
        
        Args:
            data: 要保存的数据
            filename_prefix: 文件名前缀
            
        Returns:
            保存的文件路径信息
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存原始数据
        raw_filename = f"{filename_prefix}_{timestamp}.json"
        raw_filepath = self.raw_data_dir / raw_filename
        
        with open(raw_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # 如果有解析后的内容，也保存解析数据
        parsed_filepath = None
        if 'parsed_data' in data:
            parsed_filename = f"{filename_prefix}_parsed_{timestamp}.json"
            parsed_filepath = self.parsed_data_dir / parsed_filename
            
            with open(parsed_filepath, 'w', encoding='utf-8') as f:
                json.dump(data['parsed_data'], f, ensure_ascii=False, indent=2)
                
        return {
            'raw_file': str(raw_filepath),
            'parsed_file': str(parsed_filepath) if parsed_filepath else None
        }
        
    def crawl_and_parse(self, url: str, save_data: bool = True) -> Dict[str, Any]:
        """爬取并解析网页
        
        Args:
            url: 目标网址
            save_data: 是否保存数据到文件
            
        Returns:
            包含原始数据和解析数据的完整结果
        """
        # 获取网页内容
        raw_data = self.fetch_webpage(url)
        
        if not raw_data['success']:
            logger.error(f"获取网页失败: {raw_data['error']}")
            return raw_data
            
        # 解析内容
        parsed_data = None
        if 'csdn.net' in url:
            parsed_data = self.parse_csdn_article(raw_data['content'], url)
        else:
            # 通用解析
            soup = BeautifulSoup(raw_data['content'], 'html.parser')
            parsed_data = {
                'title': soup.title.get_text().strip() if soup.title else '',
                'content': soup.get_text().strip(),
                'url': url,
                'parsed_at': datetime.now().isoformat()
            }
            
        result = {
            'raw_data': raw_data,
            'parsed_data': parsed_data,
            'success': True
        }
        
        # 保存数据
        if save_data:
            domain = urlparse(url).netloc.replace('.', '_')
            title_part = parsed_data.get('title', 'untitled')[:50]
            # 清理文件名中的特殊字符
            title_part = re.sub(r'[<>:"/\\|?*]', '_', title_part)
            filename_prefix = f"{domain}_{title_part}"
            
            file_paths = self.save_data(result, filename_prefix)
            result['file_paths'] = file_paths
            
        return result
        
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'session'):
            self.session.close()