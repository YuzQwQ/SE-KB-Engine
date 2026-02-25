#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页爬虫模块
专门用于爬取网页内容，支持CSDN等网站。

增强：
- 首选 httpx + BeautifulSoup 静态抓取与解析
- 若正文过少或解析失败，则回退到 Playwright 动态渲染抓取
"""

import httpx
import os
import time
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import logging
from .html_cleaner import clean_html_content, clean_and_structure
from .image_analyzer import analyze_images as analyze_images_fn
from .playwright_fetcher import fetch_rendered_html_sync

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
        
        # 默认请求头，模拟真实浏览器（可选：随机化 UA 与语言）
        import os as _os
        import random as _rnd
        use_random = _os.getenv('HTTPX_RANDOM_UA', '1').strip() not in ('0', 'false', 'False')
        ua_pool = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        self.headers = {
            'User-Agent': _rnd.choice(ua_pool) if use_random else ua_pool[0],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': _rnd.choice(['zh-CN,zh;q=0.9,en;q=0.8', 'en-US,en;q=0.9,zh-CN;q=0.6']) if use_random else 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'no-cache'
        }
        
        # httpx 客户端配置（按需创建）
        self._client: Optional[httpx.Client] = None

    def _get_client(self, timeout: int = 20, follow_redirects: bool = True) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers=self.headers,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )
        else:
            # 更新超时与跳转设置（避免复用导致不一致）
            self._client.timeout = timeout
            self._client.follow_redirects = follow_redirects
        return self._client

    def fetch_webpage(self, url: str, timeout: int = 20, retry_times: int = 3) -> Dict[str, Any]:
        """使用 httpx 获取网页内容（静态抓取）
        
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
                
                client = self._get_client(timeout=timeout)
                # 轻量随机停顿，模拟人类节奏
                try:
                    import random as _r
                    time.sleep(_r.uniform(0.4, 1.6))
                except Exception:
                    pass
                response = client.get(url)
                response.raise_for_status()
                
                # 检测编码
                # httpx 会自动推断编码，保持默认即可；如需强制可在此调整
                
                result = {
                    'url': url,
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content': response.text,
                    'encoding': response.encoding,
                    'timestamp': datetime.now().isoformat(),
                    'success': True,
                    'error': None,
                    'source': 'httpx'
                }
                
                logger.info(f"成功获取网页内容，状态码: {response.status_code}")
                return result
                
            except httpx.HTTPError as e:
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
                        'error': str(e),
                        'source': 'httpx'
                    }
        return {
            'url': url,
            'status_code': None,
            'headers': {},
            'content': '',
            'encoding': None,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'error': 'retry_exhausted',
            'source': 'httpx'
        }

    @staticmethod
    def _looks_dynamic(html: str) -> bool:
        markers = [
            '__NUXT__', 'data-reactroot', 'id="__next"', 'ng-version',
            'skeleton', 'loading', 'id="root"', 'id="app"',
            'window.__APOLLO_STATE__', '__INITIAL_STATE__'
        ]
        html_lc = (html or '').lower()
        return any(m.lower() in html_lc for m in markers)

    @staticmethod
    def _main_selector_hits(soup: BeautifulSoup) -> int:
        selectors = [
            'article', 'main', '#content', '.post', '.article', '.content',
            '[role="main"]', '.entry-content', '#content_views'
        ]
        hits = 0
        for sel in selectors:
            try:
                elems = soup.select(sel)
                if elems:
                    hits += 1
            except Exception:
                continue
        return hits

    @staticmethod
    def _compute_metrics(html: str, cleaned_text: str, soup: BeautifulSoup) -> Dict[str, Any]:
        html_len = len(html or '')
        cleaned_len = len(cleaned_text or '')
        density = (cleaned_len / html_len) if html_len else 0.0
        hits = WebpageCrawler._main_selector_hits(soup)
        dynamic = WebpageCrawler._looks_dynamic(html or '')
        return {
            'html_length': html_len,
            'cleaned_length': cleaned_len,
            'text_density': round(density, 4),
            'main_selector_hits': hits,
            'dynamic_markers_found': dynamic,
        }

    @staticmethod
    def _should_fallback(metrics: Dict[str, Any]) -> bool:
        # 触发条件：
        # 1) 命中动态指纹且正文较短；或
        # 2) 正文过少或密度偏低，同时主体选择器未命中
        if metrics.get('dynamic_markers_found') and metrics.get('cleaned_length', 0) < 2000:
            return True
        if (metrics.get('cleaned_length', 0) < 1200 or metrics.get('text_density', 0) < 0.18) and metrics.get('main_selector_hits', 0) == 0:
            return True
        return False
                    
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
                # 获取原始文本内容
                raw_content = content_elem.get_text().strip()
                # 使用HTML清理器清理内容
                content = clean_html_content(raw_content)
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
        
    def save_data(self, data: Dict[str, Any], filename_prefix: str) -> Dict[str, str | None]:
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
        
    def crawl_and_parse(self, url: str, save_data: bool = True, image_analysis_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """爬取并解析网页（httpx+bs4，必要时回退到Playwright）
        
        Args:
            url: 目标网址
            save_data: 是否保存数据到文件
            
        Returns:
            包含原始数据和解析数据的完整结果
        """
        # 1) 静态抓取
        raw_data = self.fetch_webpage(url)
        
        if not raw_data['success']:
            logger.error(f"获取网页失败: {raw_data['error']}")
            # 尝试动态渲染回退
            logger.info("尝试使用 Playwright 动态渲染进行回退...")
            import os as _os
            human_sim = _os.getenv('PLAYWRIGHT_HUMAN_SIM', '1').strip() not in ('0', 'false', 'False')
            # 若存在代理池（导出包中实现），此处支持通过环境中的 PROXY_URL/PROXY_POOL_FILE 传入单代理
            proxy_server = os.getenv('PROXY_URL') or None
            rendered_html = fetch_rendered_html_sync(url, human_simulation=human_sim, proxy_server=proxy_server)
            if rendered_html:
                raw_data = {
                    'url': url,
                    'status_code': 200,
                    'headers': {},
                    'content': rendered_html,
                    'encoding': 'utf-8',
                    'timestamp': datetime.now().isoformat(),
                    'success': True,
                    'error': None,
                    'source': 'playwright'
                }
                logger.info("动态渲染成功，继续解析页面内容。")
            else:
                logger.warning("动态渲染回退不可用或失败，尝试使用 r.jina.ai 代理抓取...")
                try:
                    proxy_url = f"https://r.jina.ai/{url}"
                    client = self._get_client()
                    resp = client.get(proxy_url)
                    resp.raise_for_status()
                    raw_data = {
                        'url': url,
                        'status_code': resp.status_code,
                        'headers': dict(resp.headers),
                        'content': resp.text,
                        'encoding': resp.encoding,
                        'timestamp': datetime.now().isoformat(),
                        'success': True,
                        'error': None,
                        'source': 'r.jina.ai'
                    }
                    logger.info("代理抓取成功，继续解析页面内容。")
                except Exception as e:
                    logger.warning(f"代理抓取失败，返回静态抓取失败结果: {e}")
                    return raw_data
            
        # 2) 解析与指标（静态）
        parsed_data = None
        soup_static = BeautifulSoup(raw_data['content'], 'html.parser')
        structured_static = clean_and_structure(raw_data['content'], url)
        metrics_static = self._compute_metrics(raw_data['content'], structured_static.get('clean_text', ''), soup_static)
        fallback_reason = None

        # 选择站点解析器
        if 'csdn.net' in url:
            csdn_data = self.parse_csdn_article(raw_data['content'], url)
            # 合并站点特定字段
            parsed_data = {**structured_static,
                           'author': csdn_data.get('author', ''),
                           'publish_time': csdn_data.get('publish_time', ''),
                           'tags': csdn_data.get('tags', [])}
            parsed_data['word_count'] = len(parsed_data.get('clean_text', '') or '')
            # 若 CSDN 解析正文过短，则也考虑回退
            if len(parsed_data.get('clean_text', '')) < 1200:
                fallback_reason = 'csdn_content_too_short'
        else:
            parsed_data = {**structured_static,
                           'url': url,
                           'parsed_at': datetime.now().isoformat()}
            parsed_data['word_count'] = len(parsed_data.get('clean_text', '') or '')

        # 3) 触发回退：Playwright 动态渲染
        if fallback_reason or self._should_fallback(metrics_static):
            logger.info(f"触发动态渲染回退: reason={fallback_reason or 'metrics'}")
            import os as _os
            human_sim = _os.getenv('PLAYWRIGHT_HUMAN_SIM', '1').strip() not in ('0', 'false', 'False')
            proxy_server = os.getenv('PROXY_URL') or None
            rendered_html = fetch_rendered_html_sync(url, human_simulation=human_sim, proxy_server=proxy_server)
            if rendered_html:
                raw_data['content'] = rendered_html
                raw_data['source'] = 'playwright'
                # 重新解析
                soup_dyn = BeautifulSoup(rendered_html, 'html.parser')
                structured_dyn = clean_and_structure(rendered_html, url)
                metrics_dyn = self._compute_metrics(rendered_html, structured_dyn.get('clean_text', ''), soup_dyn)
                if 'csdn.net' in url:
                    csdn_data = self.parse_csdn_article(rendered_html, url)
                    parsed_data = {**structured_dyn,
                                   'author': csdn_data.get('author', ''),
                                   'publish_time': csdn_data.get('publish_time', ''),
                                   'tags': csdn_data.get('tags', [])}
                else:
                    parsed_data = {**structured_dyn,
                                   'url': url,
                                   'parsed_at': datetime.now().isoformat()}
                parsed_data['word_count'] = len(parsed_data.get('clean_text', '') or '')
                metrics_static['fallback_used'] = True
                metrics_static['fallback_metrics'] = metrics_dyn
            else:
                logger.warning("Playwright 未可用或渲染失败，保留静态结果")
                metrics_static['fallback_used'] = False

        # 4) 图片文本化分析（可选）：不保存图片，不维护元数据，只写入文本输出
        if image_analysis_options is not None and parsed_data and parsed_data.get('images'):
            try:
                textual_images = analyze_images_fn(parsed_data.get('images', []), url, image_analysis_options)
                parsed_data['images'] = textual_images
                # 去除 Markdown 中的图片链接，确保知识库仅包含纯文本
                md = parsed_data.get('markdown_content') or parsed_data.get('markdown') or ''
                if md:
                    md_text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', md)
                    md_text = re.sub(r'\n{3,}', '\n\n', md_text).strip()
                    parsed_data['markdown_content'] = md_text
                    parsed_data['markdown'] = md_text
            except Exception as e:
                logger.warning(f"图片文本化分析异常: {e}")

        result = {
            'raw_data': raw_data,
            'parsed_data': parsed_data,
            'success': True,
            'metrics': metrics_static
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
        try:
            if hasattr(self, '_client') and self._client is not None:
                self._client.close()
        except Exception:
            pass
