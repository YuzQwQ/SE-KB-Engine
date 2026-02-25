#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML清理工具模块
用于清理网页爬取内容中的HTML标签和HTML实体编码
"""

import re
import html
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

logger = logging.getLogger(__name__)

class HTMLCleaner:
    """HTML内容清理器"""
    
    def __init__(self):
        # 常见的HTML标签模式
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        
        # HTML实体编码模式（包括数字和命名实体）
        self.html_entity_pattern = re.compile(r'&[a-zA-Z][a-zA-Z0-9]*;|&#[0-9]+;|&#x[0-9a-fA-F]+;')
        
        # 常见的HTML标签（用于更精确的清理）
        self.common_html_tags = [
            'br', 'p', 'div', 'span', 'a', 'img', 'strong', 'b', 'i', 'em',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'table',
            'tr', 'td', 'th', 'thead', 'tbody', 'script', 'style', 'meta',
            'link', 'title', 'head', 'body', 'html', 'nav', 'header', 'footer'
        ]
        
        # 需要替换为换行的标签
        self.line_break_tags = ['br', 'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']

        # 规则缓存
        self._rules: Optional[Dict[str, Any]] = None
        self._rules_path = Path(__file__).resolve().parent.parent / 'config' / 'html_cleaner_rules.json'
        
    def clean_html_content(self, content: str) -> str:
        """
        清理HTML内容，移除标签并解码HTML实体
        
        Args:
            content: 包含HTML标签和实体的原始内容
            
        Returns:
            清理后的纯文本内容
        """
        if not content or not isinstance(content, str):
            return ""
            
        try:
            # 1. 首先处理换行标签，将其替换为换行符
            cleaned_content = self._replace_line_break_tags(content)
            
            # 2. 移除所有HTML标签
            cleaned_content = self._remove_html_tags(cleaned_content)
            
            # 3. 解码HTML实体
            cleaned_content = self._decode_html_entities(cleaned_content)
            
            # 4. 清理多余的空白字符
            cleaned_content = self._clean_whitespace(cleaned_content)
            
            # 5. 移除残留的特殊字符
            cleaned_content = self._remove_special_chars(cleaned_content)
            
            return cleaned_content.strip()
            
        except Exception as e:
            logger.warning(f"HTML清理过程中出现错误: {str(e)}")
            # 如果清理失败，至少尝试基本的标签移除
            return self._basic_clean(content)

    # ============ 基础工具与规则加载 ============
    def _load_rules(self) -> Dict[str, Any]:
        """加载清洗规则配置"""
        default_rules = {
            "blacklist_tags": [
                "script", "style", "link", "meta", "iframe", "svg", "canvas",
                "noscript", "form", "input", "button", "footer", "header", "nav", "aside"
            ],
            "blacklist_keywords": [
                "header", "footer", "nav", "toolbar", "sidebar", "recommend", "related",
                "comment", "copyright", "login", "signup", "share", "advert", "ad-",
                "ads-", "banner", "popup", "modal", "cookie", "tip", "metadata",
                "statistics", "stat", "report", "like", "dislike", "follow",
                "breadcrumbs", "sponsor", "promotion", "marketing", "track", "analytics",
                "widget", "badge", "pager", "next-prev", "toc", "guide", "disclaimer",
                "feedback", "survey", "newsletter", "subscription", "download-btn"
            ],
            "whitelist_tags": [
                "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "img",
                "pre", "code", "blockquote", "table", "tr", "td", "th", "strong", "em",
                "b", "i", "u", "br", "figure", "figcaption"
            ],
            "main_container_selectors": [
                "article", "main", "#content", "#main-content", ".post", ".article-content",
                ".entry-content", ".content", ".entry", ".markdown-body", "[role=main]",
                "#content_views"
            ],
            "scoring": {
                "text_len_min": 800,
                "link_density_max": 0.4,
                "noise_penalty_per_hit": 0.3,
                "list_ratio_penalty": 0.2,
                "heading_ratio_penalty": 0.2
            },
            "image_filters": {
                "min_width": 48,
                "min_height": 48,
                "filename_exclude_keywords": [
                    "avatar", "logo", "icon", "qr", "qrcode", "barcode", "ads", "ad",
                    "banner", "tracker", "spacer", "blank"
                ]
            },
            "text_normalization": {
                "remove_emoji": False,
                "max_consecutive_newlines": 2
            },
            "markdown_options": {
                "table_style": "pipe",
                "infer_code_language": False
            },
            "domain_overrides": {}
        }
        try:
            if self._rules_path.exists():
                with open(self._rules_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 合并默认与文件规则
                    default_rules.update(data)
            else:
                logger.info("未找到html_cleaner_rules.json，使用默认规则")
        except Exception as e:
            logger.warning(f"加载清洗规则失败，使用默认规则: {e}")
        return default_rules

    def get_rules(self) -> Dict[str, Any]:
        if self._rules is None:
            self._rules = self._load_rules()
        return self._rules
    
    def _replace_line_break_tags(self, content: str) -> str:
        """将换行标签替换为换行符"""
        # 替换 <br>, <br/>, <br /> 等换行标签
        content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
        
        # 替换块级元素标签为换行符
        for tag in self.line_break_tags:
            if tag != 'br':  # br已经处理过了
                # 开始标签
                content = re.sub(f'<{tag}[^>]*>', '\n', content, flags=re.IGNORECASE)
                # 结束标签
                content = re.sub(f'</{tag}>', '\n', content, flags=re.IGNORECASE)
        
        return content
    
    def _remove_html_tags(self, content: str) -> str:
        """移除所有HTML标签"""
        # 移除HTML注释
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # 移除script和style标签及其内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除所有其他HTML标签
        content = self.html_tag_pattern.sub('', content)
        
        return content
    
    def _decode_html_entities(self, content: str) -> str:
        """解码HTML实体"""
        try:
            # 使用html.unescape解码标准HTML实体
            content = html.unescape(content)
            
            # 处理一些特殊的编码情况
            # 处理&#xff08; &#xff09; 这类Unicode编码
            def decode_unicode_entity(match):
                entity = match.group(0)
                try:
                    if entity.startswith('&#x'):
                        # 十六进制Unicode编码
                        code = int(entity[3:-1], 16)
                        return chr(code)
                    elif entity.startswith('&#'):
                        # 十进制Unicode编码
                        code = int(entity[2:-1])
                        return chr(code)
                    else:
                        return entity
                except (ValueError, OverflowError):
                    return entity
            
            # 解码Unicode实体
            content = re.sub(r'&#x?[0-9a-fA-F]+;', decode_unicode_entity, content)
            
            return content
            
        except Exception as e:
            logger.warning(f"HTML实体解码失败: {str(e)}")
            return content
    
    def _clean_whitespace(self, content: str) -> str:
        """清理多余的空白字符"""
        # 将多个连续的空白字符替换为单个空格
        content = re.sub(r'\s+', ' ', content)
        
        # 将多个连续的换行符替换为单个换行符
        content = re.sub(r'\n\s*\n', '\n', content)
        
        # 移除行首行尾的空白字符
        lines = content.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        return '\n'.join(cleaned_lines)
    
    def _remove_special_chars(self, content: str) -> str:
        """移除残留的特殊字符"""
        # 移除一些常见的残留字符
        content = re.sub(r'[^\w\s\u4e00-\u9fff\u3000-\u303f\uff00-\uffef.,!?;:()\[\]{}"\'-]', ' ', content)
        
        # 再次清理空白字符
        content = re.sub(r'\s+', ' ', content)
        
        return content
    
    def _basic_clean(self, content: str) -> str:
        """基本清理，作为备用方案"""
        try:
            # 简单移除HTML标签
            content = re.sub(r'<[^>]+>', '', content)
            # 简单解码HTML实体
            content = html.unescape(content)
            # 清理空白字符
            content = re.sub(r'\s+', ' ', content)
            return content.strip()
        except Exception:
            return content
    
    def is_html_content(self, content: str) -> bool:
        """检测内容是否包含HTML标签或实体"""
        if not content:
            return False
            
        # 检查是否包含HTML标签
        if self.html_tag_pattern.search(content):
            return True
            
        # 检查是否包含HTML实体
        if self.html_entity_pattern.search(content):
            return True
            
        return False

    # ============ 结构化清洗管线 ============
    def _basic_tag_cleanup(self, soup: 'BeautifulSoup', rules: Dict[str, Any]) -> None:
        # 移除黑名单标签
        for tag in rules.get('blacklist_tags', []):
            for t in soup.find_all(tag):
                t.decompose()

        # 移除注释
        for comment in soup.find_all(string=lambda s: isinstance(s, type(s)) and False):
            # BeautifulSoup 不直接提供注释类型判断，这里留空（注释已在文本清理中处理）
            pass

    def _remove_blacklist_nodes(self, soup: 'BeautifulSoup', rules: Dict[str, Any]) -> int:
        keywords = [k.lower() for k in rules.get('blacklist_keywords', [])]
        hits = 0
        # 使用属性匹配
        for kw in keywords:
            # class 包含关键词
            for el in soup.select(f'[class*="{kw}"]'):
                el.decompose()
                hits += 1
            # id 包含关键词
            for el in soup.select(f'[id*="{kw}"]'):
                el.decompose()
                hits += 1
        return hits

    def _link_density(self, node: 'BeautifulSoup') -> float:
        text = node.get_text(strip=True) if node else ''
        total = len(text)
        link_text = ''.join(a.get_text(strip=True) for a in node.find_all('a')) if node else ''
        return (len(link_text) / total) if total > 0 else 0.0

    def _ratio(self, node: 'BeautifulSoup', tags: List[str]) -> float:
        total = len(node.find_all(True)) if node else 0
        if total == 0:
            return 0.0
        count = 0
        for t in tags:
            count += len(node.find_all(t))
        return count / total

    def _score_container(self, node: 'BeautifulSoup', rules: Dict[str, Any]) -> float:
        scoring = rules.get('scoring', {})
        text = self.clean_html_content(node.get_text("\n"))
        text_len = len(text)
        ld = self._link_density(node)
        noise_hits = 0
        # 简化：统计一次关键词命中作为惩罚（避免重复移除影响）
        for kw in [k.lower() for k in rules.get('blacklist_keywords', [])]:
            attrs = ' '.join(filter(None, [
                ' '.join(node.get('class', [])) if node.has_attr('class') else '',
                node.get('id', '')
            ])).lower()
            if kw in attrs:
                noise_hits += 1

        list_ratio = self._ratio(node, ['ul', 'ol', 'li'])
        heading_ratio = self._ratio(node, ['h1', 'h2', 'h3'])
        score = text_len * (1 - ld) * (1 - noise_hits * scoring.get('noise_penalty_per_hit', 0.3))
        score *= (1 - list_ratio * scoring.get('list_ratio_penalty', 0.2))
        score *= (1 - heading_ratio * scoring.get('heading_ratio_penalty', 0.2))
        return score

    def _locate_main_content(self, soup: 'BeautifulSoup', base_url: str, rules: Dict[str, Any]) -> Optional['BeautifulSoup']:
        # 优先规则选择器
        overrides = rules.get('domain_overrides', {})
        domain = urlparse(base_url).netloc
        domain_rules = None
        for key, cfg in overrides.items():
            if key in domain:
                domain_rules = cfg
                break

        selectors = list(rules.get('main_container_selectors', []))
        if domain_rules and 'main_selectors' in domain_rules:
            selectors = domain_rules['main_selectors'] + selectors

        for sel in selectors:
            try:
                el = soup.select_one(sel)
            except Exception:
                el = None
            if el:
                return el

        # 评分选择
        candidates = soup.find_all(['article', 'main', 'section', 'div'])
        best = None
        best_score = 0
        for c in candidates:
            s = self._score_container(c, rules)
            if s > best_score:
                best, best_score = c, s
        return best or soup.body or soup

    def _internal_cleanup(self, node: 'BeautifulSoup', rules: Dict[str, Any]) -> None:
        # 域名覆盖的移除选择器
        # 再次移除黑名单标签与关键词
        self._basic_tag_cleanup(node, rules)
        self._remove_blacklist_nodes(node, rules)

        # 删除空标签与空白节点
        self._remove_empty_nodes(node)

    def _unwrap_non_whitelist(self, node: 'BeautifulSoup', rules: Dict[str, Any]) -> None:
        whitelist = set(rules.get('whitelist_tags', []))
        for el in list(node.find_all(True)):
            if el.name not in whitelist:
                # 保留文本与子结构，移除外壳
                el.unwrap()

    def _remove_empty_nodes(self, node: 'BeautifulSoup') -> None:
        # 递归删除不含可见文本且无重要子内容的标签
        important = {"img", "pre", "code", "table", "tr", "td", "th", "blockquote", "br"}
        for el in list(node.find_all(True)):
            # 如果是重要标签则跳过
            if el.name in important:
                continue
            text = el.get_text(strip=True)
            # 包含子图片或代码/表格则保留
            has_important_child = any(child.name in important for child in el.find_all(True))
            if not text and not has_important_child:
                el.decompose()

    def _ensure_continuity(self, soup: 'BeautifulSoup', container: 'BeautifulSoup', rules: Dict[str, Any]) -> 'BeautifulSoup':
        # 若段落过少或文本偏短，尝试提升到父级以获得连贯正文
        scoring = rules.get('scoring', {})
        min_len = scoring.get('text_len_min', 800)
        def stats(node):
            txt = self.clean_html_content(node.get_text("\n"))
            return len(txt), len(node.find_all('p'))
        length, p_count = stats(container)
        if p_count >= 5 and length >= min_len:
            return container
        current = container
        for _ in range(2):  # 最多上升两层
            parent = current.parent if hasattr(current, 'parent') else None
            if not parent or getattr(parent, 'name', None) is None:
                break
            # 仅考虑常见容器父级
            if parent.name not in ['div', 'section', 'article', 'main']:
                break
            plength, ppcount = stats(parent)
            if plength > length * 1.2 and ppcount >= p_count:
                current = parent
                length, p_count = plength, ppcount
            else:
                break
        return current

    def _extract_title(self, soup: 'BeautifulSoup', container: Optional['BeautifulSoup']) -> str:
        # 优先容器内的 h1
        if container:
            h1 = container.find('h1')
            if h1 and h1.get_text(strip=True):
                return h1.get_text(strip=True)
        # 元数据
        meta = soup.find('meta', attrs={'property': 'og:title'}) or soup.find('meta', attrs={'name': 'twitter:title'})
        if meta and meta.get('content'):
            return meta.get('content').strip()
        # 文档title
        if soup.title and soup.title.get_text(strip=True):
            return soup.title.get_text(strip=True)
        return ''

    def _sections_from_container(self, container: 'BeautifulSoup') -> List[Dict[str, Any]]:
        sections: List[Dict[str, Any]] = []
        current = {"heading": None, "level": None, "text": "", "lists": [], "images": [], "code_blocks": [], "tables": []}

        def flush():
            nonlocal current
            if current["heading"] or current["text"].strip() or current["lists"] or current["images"] or current["code_blocks"] or current["tables"]:
                sections.append(current)
            current = {"heading": None, "level": None, "text": "", "lists": [], "images": [], "code_blocks": [], "tables": []}

        for el in container.descendants:
            if not getattr(el, 'name', None):
                continue
            name = el.name
            if name in ['h1', 'h2', 'h3']:
                flush()
                current["heading"] = el.get_text(strip=True)
                current["level"] = int(name[1])
            elif name == 'p':
                txt = el.get_text(" ", strip=True)
                if txt:
                    current["text"] += (txt + "\n")
            elif name in ['ul', 'ol']:
                items = []
                for li in el.find_all('li'):
                    t = li.get_text(" ", strip=True)
                    if t:
                        items.append(t)
                if items:
                    current["lists"].extend(items)
            elif name in ['pre', 'code']:
                code_text = el.get_text("\n", strip=True)
                if code_text:
                    current["code_blocks"].append(code_text)
            elif name == 'table':
                rows = []
                for tr in el.find_all('tr'):
                    row = [td.get_text(" ", strip=True) for td in tr.find_all(['th', 'td'])]
                    if row:
                        rows.append(row)
                if rows:
                    current["tables"].append(rows)
            elif name == 'img':
                alt = el.get('alt', '')
                src = el.get('src') or el.get('data-src') or ''
                if src:
                    current["images"].append({"src": src, "alt": alt})

        flush()
        return sections

    def _tables_to_markdown(self, rows: List[List[str]]) -> str:
        if not rows:
            return ''
        header = rows[0]
        md = '| ' + ' | '.join(header) + ' |\n'
        md += '| ' + ' | '.join(['---'] * len(header)) + ' |\n'
        for r in rows[1:]:
            md += '| ' + ' | '.join(r) + ' |\n'
        return md

    def _to_markdown(self, container: 'BeautifulSoup', base_url: str, rules: Dict[str, Any]) -> str:
        lines: List[str] = []
        for el in container.descendants:
            if not getattr(el, 'name', None):
                continue
            name = el.name
            if name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(name[1])
                lines.append('#' * level + ' ' + el.get_text(strip=True))
            elif name == 'p':
                txt = el.get_text(' ', strip=True)
                if txt:
                    lines.append(txt)
            elif name == 'blockquote':
                txt = el.get_text('\n', strip=True)
                if txt:
                    for line_text in txt.splitlines():
                        lines.append('> ' + line_text)
            elif name in ['ul', 'ol']:
                for i, li in enumerate(el.find_all('li', recursive=False)):
                    txt = li.get_text(' ', strip=True)
                    if txt:
                        prefix = ('- ' if name == 'ul' else f'{i+1}. ')
                        lines.append(prefix + txt)
            elif name in ['pre', 'code']:
                code_text = el.get_text('\n', strip=True)
                if code_text:
                    lines.append('```')
                    lines.append(code_text)
                    lines.append('```')
            elif name == 'table':
                rows = []
                for tr in el.find_all('tr'):
                    row = [td.get_text(' ', strip=True) for td in tr.find_all(['th', 'td'])]
                    if row:
                        rows.append(row)
                md = self._tables_to_markdown(rows)
                if md:
                    lines.append(md.strip())
            elif name == 'img':
                alt = el.get('alt', '')
                src = el.get('src') or el.get('data-src') or ''
                if src:
                    # 标准化URL
                    full = self._normalize_image_url(base_url, src)
                    lines.append(f'![{alt}]({full})')
        # 合并并规范化换行
        md = '\n\n'.join([line for line in lines if line.strip()])
        max_n = self.get_rules().get('text_normalization', {}).get('max_consecutive_newlines', 2)
        md = re.sub(r'(\n){' + str(max_n+1) + r',}', '\n' * max_n, md)
        return md.strip()

    def _normalize_image_url(self, base_url: str, img_url: str) -> str:
        if not img_url:
            return ''
        if img_url.startswith(('http://', 'https://')):
            return img_url
        if img_url.startswith('//'):
            return 'https:' + img_url
        return urljoin(base_url, img_url)

    def _filter_images(self, images: List[Dict[str, str]], base_url: str, rules: Dict[str, Any]) -> List[Dict[str, str]]:
        result = []
        exclude_keywords = [k.lower() for k in rules.get('image_filters', {}).get('filename_exclude_keywords', [])]
        for img in images:
            src = img.get('src') or ''
            alt = img.get('alt', '')
            full = self._normalize_image_url(base_url, src)
            lower = full.lower()
            if any(k in lower for k in exclude_keywords):
                continue
            result.append({"src": full, "alt": alt, "caption": img.get('caption', '')})
        # 去重
        seen = set()
        deduped = []
        for i in result:
            if i['src'] in seen:
                continue
            seen.add(i['src'])
            deduped.append(i)
        return deduped

    def clean_and_structure(self, html_content: str, base_url: str) -> Dict[str, Any]:
        """按规则清洗并输出结构化数据"""
        if not html_content:
            return {
                'title': '', 'source_url': base_url, 'clean_text': '',
                'markdown': '', 'sections': [], 'images': []
            }
        if BeautifulSoup is None:
            # 无BS4时退化为纯文本
            cleaned = self.clean_html_content(html_content)
            return {
                'title': '', 'source_url': base_url, 'clean_text': cleaned,
                'markdown': cleaned, 'sections': [], 'images': []
            }

        rules = self.get_rules()
        soup = BeautifulSoup(html_content, 'html.parser')

        # 基础清理
        self._basic_tag_cleanup(soup, rules)
        self._remove_blacklist_nodes(soup, rules)

        # 定位正文容器
        container = self._locate_main_content(soup, base_url, rules)
        if container is None:
            container = soup.body or soup

        # 容器内部清理与解包
        self._internal_cleanup(container, rules)
        self._unwrap_non_whitelist(container, rules)

        # 连贯性检查与可能的上升
        container = self._ensure_continuity(soup, container, rules)

        # 结构提取
        title = self._extract_title(soup, container)
        clean_text = self.clean_html_content(container.get_text('\n'))
        clean_text = self._remove_invisible_and_emoji(clean_text, rules)

        # sections
        sections = self._sections_from_container(container)

        # markdown
        markdown = self._to_markdown(container, base_url, rules)

        # images（从sections与容器提取并过滤）
        raw_images = []
        for sec in sections:
            for img in sec.get('images', []):
                raw_images.append(img)
        for el in container.find_all('img'):
            raw_images.append({'src': el.get('src') or el.get('data-src') or '', 'alt': el.get('alt', '')})
        images = self._filter_images(raw_images, base_url, rules)

        return {
            'title': title or '',
            'source_url': base_url,
            'clean_text': clean_text,
            'markdown': markdown,
            'markdown_content': markdown,
            'sections': sections,
            'structured_json': sections,
            'images': images
        }

    def _remove_invisible_and_emoji(self, text: str, rules: Dict[str, Any]) -> str:
        if not text:
            return text
        # 移除零宽与不可见控制字符
        invisible_ranges = [
            '\u200B', '\u200C', '\u200D', '\u2060', '\uFEFF', '\u200E', '\u200F'
        ]
        for ch in invisible_ranges:
            text = text.replace(ch, '')
        # 可选移除 Emoji
        remove_emoji = rules.get('text_normalization', {}).get('remove_emoji', True)
        if remove_emoji:
            emoji_pattern = re.compile(
                '[\U0001F600-\U0001F64F]'  # Emoticons
                '|[\U0001F300-\U0001F5FF]'  # Symbols & pictographs
                '|[\U0001F680-\U0001F6FF]'  # Transport & map
                '|[\U0001F1E0-\U0001F1FF]'  # Flags
                '|[\u2600-\u26FF]'          # Misc symbols
                '|[\u2700-\u27BF]'          # Dingbats
                '|[\uFE0F]'                  # Variation selector
                , flags=re.UNICODE)
            text = emoji_pattern.sub('', text)
        # 规整换行（最多两连）
        max_n = rules.get('text_normalization', {}).get('max_consecutive_newlines', 2)
        text = re.sub(r'(\n){' + str(max_n+1) + r',}', '\n' * max_n, text)
        return text
    
    def clean_html_with_structure(self, content: str) -> dict:
        """
        清理HTML内容，同时保留标题结构信息
        
        Args:
            content: 包含HTML标签和实体的原始内容
            
        Returns:
            包含清理后内容和标题结构的字典
        """
        if not content or not isinstance(content, str):
            return {"cleaned_content": "", "title_structure": []}
            
        try:
            # 1. 首先提取标题结构
            title_structure = self._extract_title_structure(content)
            
            # 2. 然后进行常规清理
            cleaned_content = self.clean_html_content(content)
            
            return {
                "cleaned_content": cleaned_content,
                "title_structure": title_structure
            }
            
        except Exception as e:
            logger.warning(f"HTML结构化清理过程中出现错误: {str(e)}")
            # 如果结构化清理失败，至少返回基本清理结果
            return {
                "cleaned_content": self.clean_html_content(content),
                "title_structure": []
            }
    
    def _extract_title_structure(self, content: str) -> list:
        """提取HTML中的标题结构（h1-h3）"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            title_structure = []
            
            # 查找所有h1-h3标签
            for tag in soup.find_all(['h1', 'h2', 'h3']):
                level = int(tag.name[1])  # 提取数字部分
                text = tag.get_text(strip=True)
                
                if text:  # 只保留有内容的标题
                    title_structure.append({
                        "level": level,
                        "text": text,
                        "tag": tag.name
                    })
            
            return title_structure
            
        except ImportError:
            # 如果没有BeautifulSoup，使用正则表达式作为备选方案
            return self._extract_title_structure_regex(content)
        except Exception as e:
            logger.warning(f"标题结构提取失败: {str(e)}")
            return []
    
    def _extract_title_structure_regex(self, content: str) -> list:
        """使用正则表达式提取标题结构（备选方案）"""
        title_structure = []
        
        # 匹配h1-h3标签及其内容
        pattern = r'<(h[1-3])[^>]*>(.*?)</\1>'
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        
        for tag, text in matches:
            level = int(tag[1])
            # 清理标题文本中的HTML标签和实体
            clean_text = self._remove_html_tags(text)
            clean_text = self._decode_html_entities(clean_text)
            clean_text = clean_text.strip()
            
            if clean_text:
                title_structure.append({
                    "level": level,
                    "text": clean_text,
                    "tag": tag.lower()
                })
        
        return title_structure
    
    def format_title_structure_as_context(self, title_structure: list) -> str:
        """将标题结构格式化为上下文字符串"""
        if not title_structure:
            return ""
        
        context_lines = ["=== 文档结构 ==="]
        
        for title in title_structure:
            level = title["level"]
            text = title["text"]
            
            # 根据层级添加缩进
            indent = "  " * (level - 1)
            prefix = "#" * level
            
            context_lines.append(f"{indent}{prefix} {text}")
        
        context_lines.append("=== 正文内容 ===")
        
        return "\n".join(context_lines)

    def get_cleaning_stats(self, original: str, cleaned: str) -> dict:
        """获取清理统计信息"""
        if not original:
            return {"original_length": 0, "cleaned_length": 0, "reduction_ratio": 0}
            
        original_length = len(original)
        cleaned_length = len(cleaned)
        reduction_ratio = (original_length - cleaned_length) / original_length if original_length > 0 else 0
        
        # 统计移除的HTML标签数量
        html_tags_count = len(self.html_tag_pattern.findall(original))
        
        # 统计移除的HTML实体数量
        html_entities_count = len(self.html_entity_pattern.findall(original))
        
        return {
            "original_length": original_length,
            "cleaned_length": cleaned_length,
            "reduction_ratio": round(reduction_ratio, 3),
            "html_tags_removed": html_tags_count,
            "html_entities_removed": html_entities_count
        }


# 创建全局实例
html_cleaner = HTMLCleaner()

def clean_html_content(content: str) -> str:
    """便捷函数：清理HTML内容"""
    return html_cleaner.clean_html_content(content)

def clean_html_with_structure(content: str) -> dict:
    """便捷函数：清理HTML内容并保留标题结构"""
    return html_cleaner.clean_html_with_structure(content)

def is_html_content(content: str) -> bool:
    """便捷函数：检测是否为HTML内容"""
    return html_cleaner.is_html_content(content)

def clean_and_structure(html: str, base_url: str) -> Dict[str, Any]:
    """便捷函数：结构化清洗输出"""
    return html_cleaner.clean_and_structure(html, base_url)
