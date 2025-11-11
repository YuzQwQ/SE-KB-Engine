#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML清理工具模块
用于清理网页爬取内容中的HTML标签和HTML实体编码
"""

import re
import html
import logging

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
        except:
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