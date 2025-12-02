from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


DEFAULT_SELECTORS = [
    'article', 'main', '#content', '.post', '.article', '.content',
    '[role="main"]', '.entry-content'
]


def _load_domain_rules(base_url: Optional[str]) -> Dict[str, Any]:
    try:
        rules_path = Path(__file__).resolve().parent.parent / 'config' / 'html_cleaner_rules.json'
        if rules_path.exists():
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            domain = urlparse(base_url or '').netloc
            return rules.get(domain, {})
    except Exception:
        pass
    return {}


def _normalize_image_url(src: str, base_url: Optional[str]) -> str:
    if not src:
        return ''
    src = src.strip()
    if src.startswith('data:'):
        return src
    if src.startswith('http://') or src.startswith('https://'):
        return src
    if base_url:
        try:
            return urljoin(base_url, src)
        except Exception:
            return src
    return src


def _filter_images(images: List[Dict[str, Any]], exclude_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    exclude_keywords = (exclude_keywords or [])
    seen = set()
    filtered: List[Dict[str, Any]] = []
    for img in images:
        u = img.get('abs_url') or img.get('src') or ''
        if not u:
            continue
        low = u.lower()
        if any(k in low for k in exclude_keywords):
            continue
        if u in seen:
            continue
        seen.add(u)
        filtered.append(img)
    return filtered


def _remove_invisible_and_emoji(text: str) -> str:
    if not text:
        return ''
    # 去除零宽字符与控制符
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
    # 统一换行
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def clean_and_structure(html: str, base_url: Optional[str]) -> Dict[str, Any]:
    """清洗 HTML 并抽取结构化内容（标题、正文、图片）。

    返回：{
      title, source_url, clean_text, markdown, sections, images
    }
    """
    soup = BeautifulSoup(html or '', 'lxml')

    # 基础去噪
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()

    # 标题
    title = ''
    t1 = soup.select_one('title')
    if t1 and t1.get_text():
        title = t1.get_text().strip()
    if not title:
        for sel in ['h1', '.title', 'h2']:
            e = soup.select_one(sel)
            if e and e.get_text():
                title = e.get_text().strip()
                break

    # 主体选择器（含站点规则）
    domain_rules = _load_domain_rules(base_url)
    selectors = list(DEFAULT_SELECTORS)
    if domain_rules and 'main_selectors' in domain_rules:
        selectors = domain_rules['main_selectors'] + selectors

    main_blocks: List[str] = []
    for sel in selectors:
        try:
            elems = soup.select(sel)
            if elems:
                for e in elems:
                    text = e.get_text(' ', strip=True)
                    if text and len(text) > 200:
                        main_blocks.append(text)
        except Exception:
            continue

    if not main_blocks:
        # 兜底使用 body 文本
        body = soup.select_one('body') or soup
        main_blocks = [body.get_text('\n', strip=True)]

    clean_text = _remove_invisible_and_emoji('\n\n'.join(main_blocks))

    # 简单 markdown（与 clean_text 等价，便于兼容下游）
    markdown = clean_text

    # 图片抽取与归一化
    raw_images: List[Dict[str, Any]] = []
    exclude_keywords = domain_rules.get('exclude_keywords', []) if domain_rules else []
    for img in soup.select('img'):
        try:
            src = img.get('src') or ''
            alt = img.get('alt') or ''
            title_attr = img.get('title') or ''
            abs_url = _normalize_image_url(src, base_url)
            raw_images.append({
                'src': src,
                'abs_url': abs_url,
                'alt': alt,
                'title': title_attr,
            })
        except Exception:
            continue

    images = _filter_images(raw_images, exclude_keywords)

    # 章节结构（简化占位）
    sections: List[Dict[str, Any]] = []

    return {
        'title': title or 'untitled',
        'source_url': base_url or '',
        'clean_text': clean_text,
        'markdown': markdown,
        'sections': sections,
        'images': images,
    }