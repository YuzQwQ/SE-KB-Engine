from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import os
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .html_cleaner_core import clean_and_structure
from .playwright_fetcher_core import fetch_rendered_html_sync
from .image_analyzer_core import analyze_images as analyze_images_fn
from .proxy_pool_core import ProxyPool


logger = logging.getLogger(__name__)


class WebpageCrawlerCore:
    def __init__(self):
        self._client: Optional[httpx.Client] = None
        base = Path(__file__).resolve().parent.parent  # export/crawler_core
        data_dir = base / 'data'
        self.raw_data_dir = data_dir / 'raw'
        self.parsed_data_dir = data_dir / 'parsed'
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_data_dir.mkdir(parents=True, exist_ok=True)
        # 代理池
        self.proxy_pool = ProxyPool(base_dir=base)

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            # 可选：随机化 UA 与语言，降低固定指纹（可通过 HTTPX_RANDOM_UA=0 关闭）
            import random as _rnd
            use_random = os.getenv('HTTPX_RANDOM_UA', '1').strip() not in ('0', 'false', 'False')
            ua_pool = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
            ]
            headers = {
                'User-Agent': _rnd.choice(ua_pool) if use_random else ua_pool[0],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': _rnd.choice(['zh-CN,zh;q=0.9,en;q=0.8', 'en-US,en;q=0.9,zh-CN;q=0.6']) if use_random else 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
            # 若启用代理池，创建带代理的 client
            proxy = self.proxy_pool.get_next() if self.proxy_pool.is_enabled() else None
            self._client = self.proxy_pool.create_httpx_client(proxy, headers=headers, timeout=15)
        return self._client

    def fetch_webpage(self, url: str) -> Dict[str, Any]:
        client = self._get_client()
        active_proxy = None
        if self.proxy_pool.is_enabled():
            # 简化：每次请求可选轮换代理（通过 PROXY_ROTATE_PER_REQUEST 控制）
            rotate_req = os.getenv('PROXY_ROTATE_PER_REQUEST', '1').strip() not in ('0', 'false', 'False')
            if rotate_req:
                # 重建 client 以使用下一个代理
                self._client.close()
                self._client = None
                client = self._get_client()
            # 记录当前代理（若有）
            active_proxy = self.proxy_pool.get_next()
        for attempt in range(3):
            try:
                # 轻量随机停顿，模拟人类请求节奏
                try:
                    import time as _t
                    import random as _r
                    _t.sleep(_r.uniform(0.4, 1.6))
                except Exception:
                    pass
                resp = client.get(url)
                return {
                    'url': url,
                    'status_code': resp.status_code,
                    'headers': dict(resp.headers),
                    'content': resp.text,
                    'encoding': resp.encoding,
                    'timestamp': datetime.now().isoformat(),
                    'success': True,
                    'error': None,
                    'source': 'httpx',
                }
            except Exception as e:
                logger.warning(f"静态抓取失败({attempt+1}/3): {e}")
                if self.proxy_pool.is_enabled():
                    self.proxy_pool.mark_failure(active_proxy)
        return {
            'url': url,
            'status_code': None,
            'headers': {},
            'content': '',
            'encoding': None,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'error': 'httpx request failed',
            'source': 'httpx',
        }

    @staticmethod
    def _looks_dynamic(html: str) -> bool:
        markers = [
            '__NUXT__', 'data-reactroot', 'id="__next"', 'ng-version',
            'window.__APOLLO_STATE__', '__INITIAL_STATE__', 'id="root"', 'id="app"'
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
        hits = WebpageCrawlerCore._main_selector_hits(soup)
        dynamic = WebpageCrawlerCore._looks_dynamic(html or '')
        return {
            'html_length': html_len,
            'cleaned_length': cleaned_len,
            'text_density': round(density, 4),
            'main_selector_hits': hits,
            'dynamic_markers_found': dynamic,
        }

    @staticmethod
    def _should_fallback(metrics: Dict[str, Any]) -> bool:
        if metrics.get('dynamic_markers_found') and metrics.get('cleaned_length', 0) < 2000:
            return True
        if (metrics.get('cleaned_length', 0) < 1200 or metrics.get('text_density', 0) < 0.18) and metrics.get('main_selector_hits', 0) == 0:
            return True
        return False

    def parse_csdn_article(self, html_content: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')
        title = ''
        for selector in ['h1.title-article', '.article-title-box h1', 'h1', '.title']:
            e = soup.select_one(selector)
            if e:
                title = e.get_text().strip()
                break
        author = ''
        for sel in ['.author-name', '.info .nickname', '.blog_tags .user']:
            e = soup.select_one(sel)
            if e:
                author = e.get_text().strip(); break
        publish_time = ''
        for sel in ['.time', '.date', 'time']:
            e = soup.select_one(sel)
            if e:
                publish_time = e.get_text().strip(); break
        content = ''
        for sel in ['#content_views', '.article_content', 'article']:
            e = soup.select_one(sel)
            if e:
                content = e.get_text('\n', strip=True); break
        tags = []
        for sel in ['.tags-box .tag-link', '.article-tags a', '.tag']:
            tags = [t.get_text().strip() for t in soup.select(sel)] or tags
        return {
            'title': title,
            'content': content,
            'author': author,
            'publish_time': publish_time,
            'tags': tags,
            'url': url,
            'word_count': len(content),
            'parsed_at': datetime.now().isoformat(),
        }

    def save_data(self, data: Dict[str, Any], filename_prefix: str) -> Dict[str, str]:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        raw_filename = f"{filename_prefix}_{timestamp}.json"
        raw_filepath = self.raw_data_dir / raw_filename
        with open(raw_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        parsed_filepath = None
        if 'parsed_data' in data:
            parsed_filename = f"{filename_prefix}_parsed_{timestamp}.json"
            parsed_filepath = self.parsed_data_dir / parsed_filename
            with open(parsed_filepath, 'w', encoding='utf-8') as f:
                json.dump(data['parsed_data'], f, ensure_ascii=False, indent=2)
        return {
            'raw_file': str(raw_filepath),
            'parsed_file': str(parsed_filepath) if parsed_filepath else None,
        }

    def crawl_and_parse(self, url: str, save_data: bool = True, image_analysis_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raw_data = self.fetch_webpage(url)
        if not raw_data['success']:
            logger.info('尝试使用 Playwright 动态渲染进行回退...')
            human_sim = os.getenv('PLAYWRIGHT_HUMAN_SIM', '1').strip() not in ('0', 'false', 'False')
            # Playwright 使用代理（若有）
            proxy_arg = None
            if self.proxy_pool.is_enabled():
                try:
                    proxy_arg = self.proxy_pool.playwright_proxy_arg(self.proxy_pool.get_next())
                except Exception:
                    proxy_arg = None
            rendered_html = fetch_rendered_html_sync(url, human_simulation=human_sim, proxy_server=(proxy_arg or {}).get('server') if proxy_arg else None)
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
                    'source': 'playwright',
                }
            else:
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
                        'source': 'r.jina.ai',
                    }
                except Exception as e:
                    logger.warning(f'代理抓取失败: {e}')
                    return raw_data

        soup_static = BeautifulSoup(raw_data['content'], 'html.parser')
        structured_static = clean_and_structure(raw_data['content'], url)
        metrics_static = self._compute_metrics(raw_data['content'], structured_static.get('clean_text', ''), soup_static)
        fallback_used = False
        fallback_reason = None

        if 'csdn.net' in url:
            csdn_data = self.parse_csdn_article(raw_data['content'], url)
            parsed_data = {**structured_static,
                           'author': csdn_data.get('author', ''),
                           'publish_time': csdn_data.get('publish_time', ''),
                           'tags': csdn_data.get('tags', [])}
            parsed_data['word_count'] = len(parsed_data.get('clean_text', '') or '')
            if len(parsed_data.get('clean_text', '')) < 1200:
                fallback_reason = 'csdn_content_too_short'
        else:
            parsed_data = {**structured_static,
                           'url': url,
                           'parsed_at': datetime.now().isoformat()}
            parsed_data['word_count'] = len(parsed_data.get('clean_text', '') or '')

        if fallback_reason or self._should_fallback(metrics_static):
            human_sim = os.getenv('PLAYWRIGHT_HUMAN_SIM', '1').strip() not in ('0', 'false', 'False')
            proxy_arg = None
            if self.proxy_pool.is_enabled():
                try:
                    proxy_arg = self.proxy_pool.playwright_proxy_arg(self.proxy_pool.get_next())
                except Exception:
                    proxy_arg = None
            rendered_html = fetch_rendered_html_sync(url, human_simulation=human_sim, proxy_server=(proxy_arg or {}).get('server') if proxy_arg else None)
            if rendered_html:
                fallback_used = True
                raw_data['content'] = rendered_html
                raw_data['source'] = 'playwright'
                soup_dyn = BeautifulSoup(rendered_html, 'html.parser')
                structured_dyn = clean_and_structure(rendered_html, url)
                _ = self._compute_metrics(rendered_html, structured_dyn.get('clean_text', ''), soup_dyn)
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
            else:
                metrics_static['fallback_used'] = False

        if image_analysis_options is not None and parsed_data and parsed_data.get('images'):
            try:
                textual_images = analyze_images_fn(parsed_data.get('images', []), url, image_analysis_options)
                parsed_data['images'] = textual_images
                md = parsed_data.get('markdown', '')
                if md:
                    md_text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', md)
                    md_text = re.sub(r'\n{3,}', '\n\n', md_text).strip()
                    parsed_data['markdown'] = md_text
            except Exception as e:
                logger.warning(f'图片文本化分析异常: {e}')

        result = {
            'raw_data': raw_data,
            'parsed_data': parsed_data,
            'success': True,
            'metrics': metrics_static,
        }
        if save_data:
            domain = urlparse(url).netloc.replace('.', '_')
            title_part = parsed_data.get('title', 'untitled')[:50]
            title_part = re.sub(r'[<>:"/\\|?*]', '_', title_part)
            filename_prefix = f"{domain}_{title_part}"
            file_paths = self.save_data(result, filename_prefix)
            result['file_paths'] = file_paths
        return result

    def __del__(self):
        try:
            if hasattr(self, '_client') and self._client is not None:
                self._client.close()
        except Exception:
            pass