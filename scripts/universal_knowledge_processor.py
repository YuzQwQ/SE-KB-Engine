import json
import re
import os
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import uuid
import string
import sys

# 添加utils目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from config.path_config import KNOWLEDGE_BASE_DIR
from html_cleaner import clean_html_content, is_html_content

# 配置日志
logger = logging.getLogger(__name__)

class UniversalKnowledgeProcessor:
    """通用知识库处理器，支持需求转换的生成和验证"""
    
    def __init__(self, config_file: str = None):
        if config_file is None:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
            config_file = os.path.join(config_dir, "universal_knowledge_template.json")
        
        self.config_file = Path(config_file)
        self.template = self._load_template()
        self.extraction_config = self.template.get('universal_knowledge_base', {}).get('extraction_config', {})
        
        # 加载系统提示词配置
        self.system_prompts_config = self._load_system_prompts_config()
        self.default_category = self.system_prompts_config.get('default_prompt_type', 'universal_knowledge')
    
    def _load_template(self) -> Dict:
        """加载通用知识库模板配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"配置文件未找到: {self.config_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise
    
    def _load_system_prompts_config(self) -> Dict:
        """加载系统提示词配置"""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
            
            # 优先使用专注版本
            focused_file = os.path.join(config_dir, "system_prompts_focused.json")
            if os.path.exists(focused_file):
                with open(focused_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # 回退到原始版本
            prompts_file = os.path.join(config_dir, "system_prompts.json")
            with open(prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("系统提示词配置文件未找到，使用默认配置")
            return {"default_prompt_type": "universal_knowledge"}
        except json.JSONDecodeError as e:
            logger.error(f"系统提示词配置文件格式错误: {e}")
            return {"default_prompt_type": "universal_knowledge"}
    
    def extract_knowledge(self, content: str, url: str = "", title: str = "", 
                         requirement_type: str = "", target_conversion_type: str = "") -> Dict:
        """从内容中提取通用知识库数据"""
        
        # 验证内容是否为有效文本
        if not self._is_valid_text_content(content):
            logger.warning(f"Content validation failed for URL: {url}. Content appears to be binary or corrupted.")
            # 返回空的知识库结构
            return self._create_empty_knowledge_base(url, title, requirement_type, target_conversion_type)
        
        # 生成唯一的知识库ID
        knowledge_id = f"kb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # 构建基础结构
        knowledge_base = {
            "metadata": {
                "knowledge_id": knowledge_id,
                "title": title or "未命名知识库",
                "description": f"从 {url} 提取的{requirement_type}到{target_conversion_type}转换知识",
                "version": "1.0.0",
                "created_time": datetime.now().isoformat(),
                "updated_time": datetime.now().isoformat(),
                "source_info": {
                    "source_url": url,
                    "source_type": "web_crawl",
                    "crawl_time": datetime.now().isoformat(),
                    "extraction_method": "自动化内容分析",
                    "reliability_score": self._calculate_reliability_score(content)
                }
            },
            "requirement_type": requirement_type,
            "target_conversion_type": target_conversion_type,
            "generation_knowledge": {
                "concepts": self._extract_concepts(content),
                "rules": self._extract_rules(content),
                "patterns": self._extract_patterns(content),
                "transformations": self._extract_transformations(content)
            },
            "validation_knowledge": {
                "criteria": self._extract_criteria(content),
                "checklist": self._extract_checklist(content),
                "error_patterns": self._extract_error_patterns(content)
            },
            "examples": {
                "input_examples": self._extract_input_examples(content),
                "output_examples": self._extract_output_examples(content),
                "transformation_examples": self._extract_transformation_examples(content)
            },
            "relationships": {
                "related_knowledge_bases": [],
                "dependency_graph": {},
                "cross_references": []
            }
        }
        
        return knowledge_base
    
    def _is_valid_text_content(self, content: str) -> bool:
        """检查内容是否为有效的文本内容"""
        if not content or not isinstance(content, str):
            return False
        
        # 检查内容长度
        if len(content) < 5:
            return False
        
        # 检查是否包含常见的二进制数据标识
        binary_indicators = ['\x00', '\xff', '\xfe']
        if any(indicator in content for indicator in binary_indicators):
            return False
        
        # 对于包含中文或基本ASCII字符的内容，放宽验证
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in content)
        has_ascii_text = any(c.isalpha() for c in content)
        
        if has_chinese or has_ascii_text:
            return True
        
        # 计算可打印字符的比例（放宽标准）
        printable_chars = sum(1 for c in content if c in string.printable or ord(c) > 127)
        printable_ratio = printable_chars / len(content)
        
        # 降低可打印字符比例要求到50%
        if printable_ratio < 0.5:
            return False
        
        return True
    
    def _create_empty_knowledge_base(self, url: str = "", title: str = "", 
                                   requirement_type: str = "", target_conversion_type: str = "") -> Dict:
        """创建空的知识库结构，用于处理无效内容"""
        knowledge_id = f"kb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        return {
            "metadata": {
                "knowledge_id": knowledge_id,
                "title": title or "无效内容知识库",
                "description": f"从 {url} 提取失败 - 内容为二进制或损坏数据",
                "version": "1.0.0",
                "created_time": datetime.now().isoformat(),
                "updated_time": datetime.now().isoformat(),
                "source_info": {
                    "source_url": url,
                    "source_type": "web_crawl",
                    "crawl_time": datetime.now().isoformat(),
                    "extraction_method": "内容验证失败",
                    "reliability_score": 0.0,
                    "error_reason": "内容为二进制数据或格式损坏"
                }
            },
            "requirement_type": requirement_type,
            "target_conversion_type": target_conversion_type,
            "generation_knowledge": {
                "concepts": [],
                "rules": [],
                "patterns": [],
                "transformations": []
            },
            "validation_knowledge": {
                "criteria": [],
                "checklist": [],
                "error_patterns": []
            },
            "examples": {
                "input_examples": [],
                "output_examples": [],
                "transformation_examples": []
            },
            "relationships": {
                "related_knowledge_bases": [],
                "dependency_graph": {},
                "cross_references": []
            }
        }
    
    def _calculate_reliability_score(self, content: str) -> float:
        """计算内容可靠性评分"""
        score = 0.5  # 基础分
        
        # 根据内容长度调整
        if len(content) > 1000:
            score += 0.2
        elif len(content) > 500:
            score += 0.1
        
        # 根据结构化程度调整
        if '步骤' in content or '流程' in content:
            score += 0.1
        if '示例' in content or '例子' in content:
            score += 0.1
        if '规则' in content or '约束' in content:
            score += 0.1
        
        return min(1.0, score)
    
    def _extract_concepts(self, content: str) -> List[Dict]:
        """提取概念定义"""
        # 清理内容，移除JSON格式残留
        cleaned_content = self._clean_content_for_extraction(content)
        
        # 如果清理后的内容太短或者看起来像JSON数据，跳过处理
        if len(cleaned_content) < 50 or self._is_json_like_content(cleaned_content):
            return []
        
        # 进一步过滤，只保留有意义的句子
        meaningful_sentences = []
        sentences = re.split(r'[.!?。！？\n]', cleaned_content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            # 跳过太短的句子
            if len(sentence) < 15:
                continue
            # 跳过包含大量特殊字符的句子
            special_char_count = sum(1 for c in sentence if c in '{}[]"\':,;')
            if len(sentence) > 0 and special_char_count / len(sentence) > 0.1:
                continue
            # 跳过包含URL或JSON字段的句子
            if any(keyword in sentence.lower() for keyword in ['http', 'www.', 'redirect_link', 'displayed_link', 'favicon', 'snippet_highlighted_words', 'organic_results', 'search_metadata']):
                continue
            # 跳过明显的JSON格式数据
            if self._is_json_like_content(sentence):
                continue
            # 保留包含中文或有意义英文的句子
            if any('\u4e00' <= c <= '\u9fff' for c in sentence) or (len(sentence) > 20 and any(c.isalpha() for c in sentence)):
                meaningful_sentences.append(sentence)
        
        if len(meaningful_sentences) < 2:
            return []
        
        concepts = []
        patterns = self.extraction_config.get('concepts', {}).get('patterns', {})
        definition_indicators = patterns.get('definition_indicators', [])
        
        # 添加更多概念关键词
        concept_keywords = ['概念', '定义', '是指', '指的是', '意思是', '表示', '代表', '包括', '包含', '用于', '通过', '可以', '需要']
        all_indicators = definition_indicators + concept_keywords
        
        for sentence in meaningful_sentences[:15]:  # 限制处理数量
            if any(keyword in sentence for keyword in all_indicators) and len(sentence) > 20:
                # 智能提取概念名称
                concept_name = self._extract_concept_name_smart(sentence, all_indicators)
                
                # 如果仍然无法提取有效名称，跳过这个句子
                if concept_name == "未知概念" or len(concept_name.strip()) < 2:
                    continue
                
                # 清理和优化定义内容
                clean_definition = self._clean_definition(sentence)
                
                # 新增：基于定义自动生成简短标题作为概念名（必要时回退）
                concept_name = self._refine_concept_name(concept_name)
                
                concept_id = f"concept_{len(concepts) + 1:03d}"
                concepts.append({
                    "concept_id": concept_id,
                    "name": concept_name,
                    "definition": clean_definition,
                    "category": "extracted",
                    "attributes": {},
                    "relationships": []
                })
        
        return concepts[:8]  # 限制返回数量

    def _extract_concept_name_smart(self, sentence: str, indicators: List[str]) -> str:
        """智能提取概念名称（增强版）"""
        # 尝试多种策略提取概念名称
        
        # 统一清理句子中的章节/编号前缀
        sentence_cleaned = re.sub(r'^(?:第\s*\d+[章节条]\s*|[一二三四五六七八九十百千]+[、.、]\s*|[一二三四五六七八九十百千]+\s+|\d+[、.、]\s*|\d+\s+)', '', sentence)
        
        # 策略1：查找定义模式 "X是指..."、"X表示..."等
        for indicator in indicators:
            if indicator in sentence_cleaned:
                parts = sentence_cleaned.split(indicator, 1)
                if len(parts) >= 2:
                    potential_name = parts[0].strip()
                    
                    # 清理潜在的概念名称并优化摘要
                    potential_name = re.sub(r'^[、，。！？：；\s]+', '', potential_name)
                    potential_name = re.sub(r'[、，。！？：；\s]+$', '', potential_name)
                    potential_name = self._refine_concept_name(potential_name)
                    
                    # 检查是否是有效的概念名称
                    if self._is_valid_concept_name(potential_name):
                        return potential_name[:20]  # 限制长度以提高可读性
        
        # 策略2：查找括号中的定义 "(概念名)"
        bracket_match = re.search(r'[（(]([^）)]+)[）)]', sentence_cleaned)
        if bracket_match:
            potential_name = bracket_match.group(1).strip()
            potential_name = self._refine_concept_name(potential_name)
            if self._is_valid_concept_name(potential_name):
                return potential_name[:20]
        
        # 策略3：查找引号中的概念 "概念名"
        quote_match = re.search(r'["""]([^"""]+)["""]', sentence_cleaned)
        if quote_match:
            potential_name = quote_match.group(1).strip()
            potential_name = self._refine_concept_name(potential_name)
            if self._is_valid_concept_name(potential_name):
                return potential_name[:20]
        
        # 策略4：提取句子开头的主语（通常是概念名）
        # 查找第一个动词或关键词之前的内容
        for indicator in ['是', '为', '指', '表示', '代表', '包括', '用于']:
            if indicator in sentence_cleaned:
                parts = sentence_cleaned.split(indicator, 1)
                if len(parts) >= 2:
                    potential_name = parts[0].strip()
                    potential_name = re.sub(r'^[、，。！？：；\s]+', '', potential_name)
                    potential_name = re.sub(r'[、，。！？：；\s]+$', '', potential_name)
                    potential_name = self._refine_concept_name(potential_name)
                    
                    if self._is_valid_concept_name(potential_name):
                        return potential_name[:20]
        
        return "未知概念"
    
    def _is_valid_concept_name(self, name: str) -> bool:
        """检查是否是有效的概念名称"""
        if not name or len(name.strip()) < 2:
            return False
        
        name = name.strip()
        
        # 排除明显不是概念名称的内容
        invalid_patterns = [
            r'^\d+[、.]',           # 数字开头的列表项
            r'^\d+\s',             # 数字+空格开头
            r'^[一二三四五六七八九十百千]+[、.]',  # 中文数字开头的列表项
            r'^[一二三四五六七八九十百千]+\s',    # 中文数字+空格开头
            r'http[s]?://',          # URL
            r'www\.',               # 网址
            r'^[第\s]*\d+[章节步骤]',  # 章节号
            r'^\s*[（(].*[）)]\s*$',  # 纯括号内容
            r'^\s*["""] .* ["""]\s*$',  # 纯引号内容
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, name):
                return False
        
        # 检查是否包含过多特殊字符
        special_char_count = sum(1 for c in name if c in '{}[]"\':,;()（）【】')
        if len(name) > 0 and special_char_count / len(name) > 0.3:
            return False
        
        # 检查长度是否合理
        if len(name) > 50:
            return False
        
        return True
    
    def _refine_concept_name(self, name: str) -> str:
        """对概念名称进行规范化处理，去除编号/噪音并保留核心词"""
        if not name:
            return name
        
        n = name.strip()
        # 去除章节/编号前缀
        n = re.sub(r'^(?:第\s*\d+[章节条]\s*|[一二三四五六七八九十百千]+[、.、]\s*|[一二三四五六七八九十百千]+\s+|\d+[、.、]\s*|\d+\s+)', '', n)
        
        # 去除常见无用后缀
        noise_suffixes = ['的定义', '的区别', '的目标', '的原则', '的过程', '简介', '概述', '总结', '说明', '介绍']
        for suf in noise_suffixes:
            n = re.sub(suf + r'$', '', n)
        
        # 若以“的”结尾，且长度>2，去除末尾“的”
        n = re.sub(r'的$', '', n) if len(n) > 2 else n
        
        # 压缩空白
        n = re.sub(r'\s+', ' ', n)
        
        # 截断过长名称，提高可读性
        if len(n) > 20:
            n = n[:20]
        
        return n
    
    def _clean_definition(self, definition: str) -> str:
        """清理和优化定义内容"""
        if not definition:
            return ""
        
        # 移除多余的空白字符
        definition = re.sub(r'\s+', ' ', definition.strip())
        
        # 移除开头的序号或标记
        definition = re.sub(r'^[0-9]+[、.]?\s*', '', definition)
        definition = re.sub(r'^[一二三四五六七八九十]+[、.]?\s*', '', definition)
        definition = re.sub(r'^[第\s]*\d+[章节步骤条]\s*[：:]\s*', '', definition)
        
        # 去除末尾孤立数字（如“1。”）
        definition = re.sub(r'[、。,，\s]*\d+\s*$', '', definition)
        
        # 确保定义以合适的标点结尾
        if definition and not definition.endswith(('。', '！', '？', '.', '!', '?')):
            definition += '。'
        
        return definition

    def _extract_rules(self, content: str) -> List[Dict]:
        """提取生成规则"""
        # 清理内容，移除JSON格式残留
        cleaned_content = self._clean_content_for_extraction(content)
        
        # 如果清理后的内容太短或者看起来像JSON数据，跳过处理
        if len(cleaned_content) < 50 or self._is_json_like_content(cleaned_content):
            return []
        
        # 进一步过滤，只保留有意义的句子
        meaningful_sentences = []
        sentences = re.split(r'[.!?。！？\n]', cleaned_content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            # 跳过太短的句子
            if len(sentence) < 15:
                continue
            # 跳过包含大量特殊字符的句子
            special_char_count = sum(1 for c in sentence if c in '{}[]"\':,;')
            if len(sentence) > 0 and special_char_count / len(sentence) > 0.1:
                continue
            # 跳过包含URL或JSON字段的句子
            if any(keyword in sentence.lower() for keyword in ['http', 'www.', 'redirect_link', 'displayed_link', 'favicon', 'snippet_highlighted_words', 'organic_results', 'search_metadata']):
                continue
            # 跳过明显的JSON格式数据
            if self._is_json_like_content(sentence):
                continue
            # 保留包含中文或有意义英文的句子
            if any('\u4e00' <= c <= '\u9fff' for c in sentence) or (len(sentence) > 20 and any(c.isalpha() for c in sentence)):
                meaningful_sentences.append(sentence)
        
        if len(meaningful_sentences) < 2:
            return []
        
        rules = []
        patterns = self.extraction_config.get('rules', {}).get('patterns', {})
        rule_indicators = patterns.get('rule_indicators', [])
        
        # 添加更多规则关键词
        rule_keywords = ['必须', '应该', '不能', '禁止', '要求', '规定', '限制', '约束', '条件', '如果', '当', '则']
        all_indicators = rule_indicators + rule_keywords
        
        for sentence in meaningful_sentences[:10]:  # 限制处理数量
            if any(keyword in sentence for keyword in all_indicators) and len(sentence) > 20:
                rule_id = f"rule_{len(rules) + 1:03d}"
                rules.append({
                    "rule_id": rule_id,
                    "type": "constraint",
                    "condition": "通用条件",
                    "action": sentence.strip(),
                    "priority": 1,
                    "applicable_scenarios": ["general"]
                })
        
        return rules[:6]  # 限制返回数量
    
    def _extract_patterns(self, content: str) -> List[Dict]:
        """提取模式模板"""
        # 清理内容，移除JSON格式残留
        cleaned_content = self._clean_content_for_extraction(content)
        
        # 如果清理后的内容太短或者看起来像JSON数据，跳过处理
        if len(cleaned_content) < 50 or self._is_json_like_content(cleaned_content):
            return []
        
        # 进一步过滤，只保留有意义的句子
        meaningful_sentences = []
        sentences = re.split(r'[.!?。！？\n]', cleaned_content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            # 跳过太短的句子
            if len(sentence) < 15:
                continue
            # 跳过包含大量特殊字符的句子
            special_char_count = sum(1 for c in sentence if c in '{}[]"\':,;')
            if len(sentence) > 0 and special_char_count / len(sentence) > 0.1:
                continue
            # 跳过包含URL或JSON字段的句子
            if any(keyword in sentence.lower() for keyword in ['http', 'www.', 'redirect_link', 'displayed_link', 'favicon', 'snippet_highlighted_words', 'organic_results', 'search_metadata']):
                continue
            # 跳过明显的JSON格式数据
            if self._is_json_like_content(sentence):
                continue
            # 跳过包含章节标记的句子
            if re.search(r'[一二三四五六七八九十]\s*[、，,]', sentence):
                continue
            # 保留包含中文或有意义英文的句子
            if any('\u4e00' <= c <= '\u9fff' for c in sentence) or (len(sentence) > 20 and any(c.isalpha() for c in sentence)):
                meaningful_sentences.append(sentence)
        
        if len(meaningful_sentences) < 2:
            return []
        
        patterns = []
        config_patterns = self.extraction_config.get('patterns', {})
        template_indicators = config_patterns.get('template_indicators', [])
        
        # 添加更多模式关键词，包含技术术语和模型相关词汇
        pattern_keywords = [
            '模式', '模板', '格式', '结构', '框架', '样式', '方法', '流程', '步骤',
            '模型', '图', '表', '算法', '技术', '策略', '原则', '规范', '标准',
            '设计', '架构', '体系', '系统', '机制', '机理', '原理', '理论',
            '分析', '建模', '实现', '解决方案', '方案', '途径', '手段', '工具'
        ]
        all_indicators = template_indicators + pattern_keywords
        
        # 查找模板模式
        for sentence in meaningful_sentences[:8]:  # 限制处理数量
            if any(indicator in sentence for indicator in all_indicators) and len(sentence) > 20:
                # 提取模式名称 - 改进逻辑
                pattern_name = self._extract_pattern_name(sentence, all_indicators)
                
                # 验证模式名称的有效性
                if self._is_valid_pattern_name(pattern_name):
                    pattern_id = f"pattern_{len(patterns) + 1:03d}"
                    patterns.append({
                        "pattern_id": pattern_id,
                        "name": pattern_name,
                        "template": sentence.strip(),
                        "variables": {},
                        "usage_context": "通用场景",
                        "complexity_level": "medium"
                    })
        
        return patterns[:5]  # 限制返回数量
    
    def _extract_pattern_name(self, sentence: str, indicators: List[str]) -> str:
        """从句子中提取模式名称"""
        # 尝试从句子开头提取主要概念
        # 移除章节标记
        cleaned_sentence = re.sub(r'^[一二三四五六七八九十]+[、，,]\s*', '', sentence)
        
        # 查找第一个有意义的名词短语
        for indicator in indicators:
            if indicator in cleaned_sentence:
                # 在指示词之前查找名称
                before_indicator = cleaned_sentence.split(indicator)[0].strip()
                if before_indicator and len(before_indicator) <= 20:
                    return before_indicator
                
                # 在指示词之后查找名称
                after_parts = cleaned_sentence.split(indicator, 1)
                if len(after_parts) > 1:
                    after_indicator = after_parts[1].strip()
                    # 提取第一个有意义的短语
                    words = after_indicator.split()[:3]  # 取前3个词
                    if words:
                        candidate = ''.join(words)
                        if len(candidate) <= 20:
                            return candidate
        
        # 如果没有找到合适的名称，从句子开头提取
        words = cleaned_sentence.split()[:2]  # 取前2个词
        if words:
            candidate = ''.join(words)
            if len(candidate) <= 20:
                return candidate
        
        return "通用模式"
    
    def _is_valid_pattern_name(self, name: str) -> bool:
        """验证模式名称是否有效"""
        if not name or len(name) < 2:
            return False
        
        # 排除无意义的名称
        invalid_patterns = [
            "未知", "通过", "基于", "进行", "实现", "完成", "处理", "分析", "设计",
            "一致性", "需求规格", "原型完善", "用户需求"
        ]
        
        for invalid in invalid_patterns:
            if invalid in name:
                return False
        
        # 排除包含章节标记的名称
        if re.search(r'[一二三四五六七八九十]\s*[、，,]', name):
            return False
        
        # 排除过长的名称
        if len(name) > 20:
            return False
        
        return True
    
    def _extract_transformations(self, content: str) -> List[Dict]:
        """提取转换方法"""
        transformations = []
        patterns = self.extraction_config.get('transformations', {})
        step_indicators = patterns.get('step_indicators', [])
        
        # 清理内容，移除可能的JSON格式残留
        cleaned_content = self._clean_content_for_extraction(content)
        
        # 如果清理后的内容太短或者看起来像JSON数据，跳过处理
        if len(cleaned_content) < 50 or self._is_json_like_content(cleaned_content):
            return []
        
        # 进一步过滤，只保留有意义的句子
        meaningful_sentences = []
        sentences = re.split(r'[。！？\n]', cleaned_content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            # 跳过太短的句子
            if len(sentence) < 15:
                continue
            # 跳过包含大量特殊字符的句子
            special_char_count = sum(1 for c in sentence if c in '{}[]"\':,;')
            if len(sentence) > 0 and special_char_count / len(sentence) > 0.1:
                continue
            # 跳过包含URL或JSON字段的句子
            if any(keyword in sentence.lower() for keyword in ['http', 'www.', 'redirect_link', 'displayed_link', 'favicon', 'snippet_highlighted_words']):
                continue
            # 跳过明显的JSON格式数据
            if self._is_json_like_content(sentence):
                continue
            # 保留包含中文或有意义英文的句子
            if any('\u4e00' <= c <= '\u9fff' for c in sentence) or (len(sentence) > 20 and any(c.isalpha() for c in sentence)):
                meaningful_sentences.append(sentence)
        
        if len(meaningful_sentences) < 2:
            return []
        
        # 查找步骤模式
        current_steps = []
        
        for sentence in meaningful_sentences[:10]:  # 限制处理数量
            if any(indicator in sentence for indicator in step_indicators) and len(sentence) > 20:
                if current_steps:
                    transformation_id = f"transform_{len(transformations) + 1:03d}"
                    transformations.append({
                        "transformation_id": transformation_id,
                        "from_format": "source",
                        "to_format": "target",
                        "steps": current_steps.copy(),
                        "tools_required": [],
                        "preconditions": []
                    })
                    current_steps = []
                current_steps.append(sentence.strip())
            elif current_steps and sentence.strip() and len(sentence) > 15:
                current_steps.append(sentence.strip())
        
        # 处理最后一组步骤
        if current_steps:
            transformation_id = f"transform_{len(transformations) + 1:03d}"
            transformations.append({
                "transformation_id": transformation_id,
                "from_format": "source",
                "to_format": "target",
                "steps": current_steps,
                "tools_required": [],
                "preconditions": []
            })
        
        return transformations[:5]  # 限制返回数量
    
    def _clean_content_for_extraction(self, content: str) -> str:
        """清理内容，移除HTML标签、JSON格式残留和特殊字符"""
        if not content:
            return ""
        
        # 首先检查并清理HTML内容
        if is_html_content(content):
            logger.info("检测到HTML内容，正在进行HTML清理...")
            content = clean_html_content(content)
        
        # 继续原有的清理逻辑，处理JSON格式残留
        meaningful_text = []
        
        # 按行分割内容
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            # 跳过空行
            if not line:
                continue
            # 跳过明显的JSON数据行
            if self._is_json_like_content(line):
                continue
            # 跳过纯URL行（更精确的判断）
            if self._is_url_line(line):
                continue
            # 跳过包含大量特殊字符的行
            special_char_count = sum(1 for c in line if c in '{}[]"\':,;')
            if len(line) > 0 and special_char_count / len(line) > 0.3:
                continue
            # 保留有意义的文本
            if len(line) > 10 and any(c.isalpha() for c in line):
                meaningful_text.append(line)
        
        # 合并有意义的文本
        cleaned = ' '.join(meaningful_text)
        
        # 进一步清理
        # 移除剩余的JSON结构标识
        cleaned = re.sub(r'[{}\[\]"\']', ' ', cleaned)
        # 移除多余的空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # 移除URL编码
        cleaned = re.sub(r'%[0-9A-Fa-f]{2}', ' ', cleaned)
        # 移除常见的JSON字段名
        cleaned = re.sub(r'\b(position|title|link|redirect_link|displayed_link|favicon|date|snippet|snippet_highlighted_words|source|search_metadata|search_parameters|organic_results|pagination)\b:?', ' ', cleaned)
        
        return cleaned.strip()
    
    def _is_url_line(self, line: str) -> bool:
        """判断是否为纯URL行"""
        line = line.strip()
        
        # 检查是否以协议开头的完整URL
        if line.startswith(('http://', 'https://', 'ftp://', 'www.')):
            # 如果行很短且主要是URL，则过滤
            if len(line) < 200 and (line.count(' ') < 3):
                return True
        
        # 检查是否包含多个URL特征但内容很少
        url_indicators = ['http://', 'https://', 'www.', '.com', '.net', '.org', '.cn']
        url_count = sum(1 for indicator in url_indicators if indicator in line)
        
        # 如果URL指示符很多但文本内容很少，可能是URL行
        if url_count >= 2 and len(line) < 100:
            return True
            
        return False
    
    def _is_json_like_content(self, text: str) -> bool:
        """检测文本是否像JSON格式数据"""
        if not text.strip():
            return False
        
        text_lower = text.lower()
        
        # 检查是否包含明显的JSON字段名
        json_fields = ['search_metadata', 'search_parameters', 'organic_results', 'pagination', 
                      'redirect_link', 'displayed_link', 'favicon', 'serpapi', 'json_endpoint',
                      'pixel_position_endpoint', 'created_at', 'processed_at', 'google_url',
                      'raw_html_file', 'total_time_taken', 'query_displayed', 'total_results',
                      'time_taken_displayed', 'organic_results_state', 'snippet_highlighted_words']
        
        if any(field in text_lower for field in json_fields):
            return True
        
        # 检查是否包含大量JSON特征
        json_indicators = ['{', '}', '[', ']', '":', "':", "'position':", '"position":']
        indicator_count = sum(1 for indicator in json_indicators if indicator in text)
        
        # 检查特殊字符比例
        special_chars = sum(1 for c in text if c in '{}[]"\':,;')
        special_ratio = special_chars / len(text) if len(text) > 0 else 0
        
        # 如果特殊字符比例过高，认为是JSON数据
        if special_ratio > 0.2:
            return True
            
        # 如果包含多个JSON指示符，认为是JSON数据
        return indicator_count >= 3 or (len(text) > 100 and indicator_count >= 2)
    
    def _extract_criteria(self, content: str) -> List[Dict]:
        """提取验证标准"""
        criteria = []
        patterns = self.extraction_config.get('validation', {})
        criteria_indicators = patterns.get('criteria_indicators', [])
        
        sentences = re.split(r'[。！？\n]', content)
        for sentence in sentences:
            if any(indicator in sentence for indicator in criteria_indicators):
                criteria_id = f"criteria_{len(criteria) + 1:03d}"
                criteria.append({
                    "criteria_id": criteria_id,
                    "name": f"标准{len(criteria) + 1}",
                    "description": sentence.strip(),
                    "measurement_method": "manual_review",
                    "threshold_values": {},
                    "weight": 1.0
                })
        
        return criteria
    
    def _extract_checklist(self, content: str) -> List[Dict]:
        """提取检查清单"""
        checklist = []
        
        # 为checklist使用专门的清理方法，保留行结构
        cleaned_content = self._clean_content_for_checklist(content)
        
        # 查找列表项模式，限制匹配长度避免匹配整个文档
        list_patterns = [
            r'\d+[.、]\s*([^。！？\n]{5,100})',  # 数字列表，限制长度
            r'[•·-]\s*([^。！？\n]{5,100})',    # 符号列表，限制长度
            r'(\d+[.、][^。！？\n]{5,100})',    # 完整的数字列表项
            r'([•·-][^。！？\n]{5,100})'       # 完整的符号列表项
        ]
        
        for pattern in list_patterns:
            matches = re.findall(pattern, cleaned_content)
            for match in matches:
                # 清理和验证匹配内容
                cleaned_match = self._clean_checklist_item(match.strip())
                
                # 验证检查项的有效性
                if self._is_valid_checklist_item(cleaned_match):
                    check_id = f"check_{len(checklist) + 1:03d}"
                    checklist.append({
                        "check_id": check_id,
                        "category": self.default_category,
                        "description": cleaned_match,
                        "validation_method": "manual",
                        "expected_result": "符合要求",
                        "severity_level": "medium"
                    })
        
        return checklist[:10]  # 限制返回数量
    
    def _clean_content_for_checklist(self, content: str) -> str:
        """为checklist提取专门清理内容，保留行结构"""
        if not content:
            return ""
        
        # 首先检查并清理HTML内容
        if is_html_content(content):
            content = clean_html_content(content)
        
        # 先按句号、感叹号、问号分割，创建更短的段落
        sentences = re.split(r'[。！？]', content)
        meaningful_lines = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 5:
                continue
                
            # 跳过明显的JSON数据行
            if self._is_json_like_content(sentence):
                continue
            # 跳过纯URL行
            if self._is_url_line(sentence):
                continue
            # 跳过包含大量特殊字符的行
            special_char_count = sum(1 for c in sentence if c in '{}[]"\':,;')
            if len(sentence) > 0 and special_char_count / len(sentence) > 0.3:
                continue
            
            # 简单清理但保留结构
            cleaned_sentence = re.sub(r'[{}\[\]"\']', ' ', sentence)
            cleaned_sentence = re.sub(r'\s+', ' ', cleaned_sentence).strip()
            
            if cleaned_sentence and len(cleaned_sentence) > 5:
                meaningful_lines.append(cleaned_sentence)
        
        # 用空格连接，但在数字列表和符号列表前添加换行
        result = ' '.join(meaningful_lines)
        
        # 在列表项前添加换行符，帮助正则表达式匹配
        result = re.sub(r'(\d+[.、])', r'\n\1', result)
        result = re.sub(r'([•·-]\s)', r'\n\1', result)
        
        return result
    
    def _is_json_like_content(self, line: str) -> bool:
        """判断是否为JSON格式的内容行"""
        # 检查是否包含JSON特征
        json_indicators = [
            line.strip().startswith('"') and line.strip().endswith('",'),
            line.strip().startswith('"') and line.strip().endswith('"'),
            '": "' in line,
            line.strip() in ['{', '}', '[', ']', ','],
            re.match(r'^\s*"[^"]*":\s*"[^"]*",?\s*$', line),
            re.match(r'^\s*\d+\s*$', line.strip()),  # 纯数字行
        ]
        return any(json_indicators)
    
    def _clean_checklist_item(self, item: str) -> str:
        """清理检查清单项"""
        # 移除引号和特殊字符
        item = re.sub(r'^["\']|["\']$', '', item)
        item = re.sub(r'[,，]\s*$', '', item)
        
        # 移除JSON格式残留
        item = re.sub(r'^\s*[\{\[\"\']|[\}\]\"\'],?\s*$', '', item)
        
        return item.strip()
    
    def _is_valid_checklist_item(self, item: str) -> bool:
        """验证检查清单项是否有效"""
        if not item or len(item) < 5:
            return False
        
        # 排除无意义的内容
        invalid_patterns = [
            r'^\d+$',  # 纯数字
            r'^[a-zA-Z]+$',  # 纯英文字母
            r'^[\{\[\]\}\"\']+$',  # 纯特殊字符
            r'json',  # JSON相关
            r'redirect_link',  # 网页元数据
            r'favicon',
            r'snippet_highlighted_words'
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, item, re.IGNORECASE):
                return False
        
        # 检查是否包含有意义的中文或英文内容
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in item)
        has_meaningful_english = len(item) > 10 and any(c.isalpha() for c in item)
        
        if not (has_chinese or has_meaningful_english):
            return False
        
        # 排除过长的项目
        if len(item) > 100:
            return False
        
        return True
    
    def _extract_error_patterns(self, content: str) -> List[Dict]:
        """提取错误模式"""
        error_patterns = []
        patterns = self.extraction_config.get('validation', {})
        error_indicators = patterns.get('error_indicators', [])
        
        sentences = re.split(r'[。！？\n]', content)
        for sentence in sentences:
            if any(indicator in sentence for indicator in error_indicators):
                error_id = f"error_{len(error_patterns) + 1:03d}"
                error_patterns.append({
                    "error_id": error_id,
                    "pattern_description": sentence.strip(),
                    "symptoms": [sentence.strip()],
                    "root_causes": [],
                    "solutions": [],
                    "prevention_measures": []
                })
        
        return error_patterns
    
    def _extract_input_examples(self, content: str) -> List[Dict]:
        """提取输入示例"""
        examples = []
        
        # 查找示例模式
        example_patterns = [r'示例[：:]([^。！？\n]+)', r'例如[：:]([^。！？\n]+)']
        
        for pattern in example_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                example_id = f"input_{len(examples) + 1:03d}"
                examples.append({
                    "example_id": example_id,
                    "title": f"输入示例{len(examples) + 1}",
                    "content": match.strip(),
                    "format": "text",
                    "complexity_level": "medium",
                    "tags": []
                })
        
        return examples
    
    def _extract_output_examples(self, content: str) -> List[Dict]:
        """提取输出示例"""
        examples = []
        
        # 查找结果模式
        result_patterns = [r'结果[：:]([^。！？\n]+)', r'输出[：:]([^。！？\n]+)']
        
        for pattern in result_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                example_id = f"output_{len(examples) + 1:03d}"
                examples.append({
                    "example_id": example_id,
                    "input_reference": "",
                    "content": match.strip(),
                    "format": "text",
                    "quality_score": 0.8,
                    "annotations": {}
                })
        
        return examples
    
    def _extract_transformation_examples(self, content: str) -> List[Dict]:
        """提取转换示例"""
        examples = []
        
        # 查找转换过程描述
        transform_patterns = [r'转换[：:]([^。！？\n]+)', r'变换[：:]([^。！？\n]+)']
        
        for pattern in transform_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                example_id = f"transform_{len(examples) + 1:03d}"
                examples.append({
                    "example_id": example_id,
                    "input_example_id": "",
                    "output_example_id": "",
                    "transformation_steps": [match.strip()],
                    "intermediate_results": [],
                    "notes": ""
                })
        
        return examples
    
    def save_knowledge_base(self, knowledge_base: Dict, output_dir: str = KNOWLEDGE_BASE_DIR) -> str:
        """保存知识库到文件，自动分类到合适的子目录"""
        
        # 确定分类子目录
        category = self._categorize_knowledge_base(knowledge_base)
        
        # 创建完整的输出目录路径
        full_output_dir = os.path.join(output_dir, category)
        os.makedirs(full_output_dir, exist_ok=True)
        
        knowledge_id = knowledge_base.get('metadata', {}).get('knowledge_id', 'unknown')
        filename = f"universal_kb_{knowledge_id}.json"
        filepath = os.path.join(full_output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
        
        logger.info(f"知识库已保存到: {filepath} (分类: {category})")
        return filepath
    
    def _categorize_knowledge_base(self, knowledge_base: Dict) -> str:
        """根据知识库内容确定分类"""
        metadata = knowledge_base.get('metadata', {})
        title = metadata.get('title', '').lower()
        description = metadata.get('description', '').lower()
        source_url = metadata.get('source_info', {}).get('source_url', '').lower()
        reliability = metadata.get('source_info', {}).get('reliability_score', 0)
        
        # 检查质量
        if reliability < 0.7:
            return 'archived'
        
        # 检查内容丰富度
        concepts_count = len(knowledge_base.get('generation_knowledge', {}).get('concepts', []))
        if concepts_count < 2:
            return 'archived'
        
        # 按主题分类
        content_text = f"{title} {description} {source_url}"
        
        # DFD相关
        if any(keyword in content_text for keyword in [
            'dfd', '数据流图', 'data flow diagram', '数据流程图', 
            '数据流', 'dataflow', '流程图建模'
        ]):
            return 'dfd_modeling'
        
        # 需求分析相关
        elif any(keyword in content_text for keyword in [
            '需求分析', 'requirement analysis', '需求工程', 'requirement engineering',
            '需求建模', '业务分析', '系统分析'
        ]):
            return 'requirement_analysis'
        
        # UML相关
        elif any(keyword in content_text for keyword in [
            'uml', 'unified modeling language', '统一建模语言', 
            '用例图', '类图', '时序图', '活动图'
        ]):
            return 'uml_modeling'
        
        # 软件工程通用
        elif any(keyword in content_text for keyword in [
            '软件工程', 'software engineering', '系统设计', 'system design',
            '软件设计', '架构设计', '设计模式'
        ]):
            return 'software_engineering'
        
        # 案例研究
        elif any(keyword in content_text for keyword in [
            '案例', 'case study', '实例', '例子', '实战', '项目',
            '应用', 'application', '实践'
        ]):
            return 'case_studies'
        
        # 默认未分类
        else:
            return 'uncategorized'
    
    def convert_from_old_format(self, old_data: Dict, requirement_type: str = "", 
                               target_conversion_type: str = "") -> Dict:
        """从旧格式转换为新的通用知识库格式"""
        
        # 提取旧格式中的元数据
        old_metadata = old_data.get('metadata', {})
        
        # 生成新的知识库ID
        knowledge_id = f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # 构建新格式
        new_knowledge_base = {
            "metadata": {
                "knowledge_id": knowledge_id,
                "title": old_metadata.get('title', '转换的知识库'),
                "description": f"从旧格式转换的{requirement_type}到{target_conversion_type}知识库",
                "version": "1.0.0",
                "created_time": datetime.now().isoformat(),
                "updated_time": datetime.now().isoformat(),
                "source_info": {
                    "source_url": old_metadata.get('source_url', ''),
                    "source_type": "format_conversion",
                    "crawl_time": old_metadata.get('crawl_time', ''),
                    "extraction_method": "格式转换",
                    "reliability_score": 0.8
                }
            },
            "requirement_type": requirement_type,
            "target_conversion_type": target_conversion_type,
            "generation_knowledge": {
                "concepts": self._convert_concepts(old_data),
                "rules": self._convert_rules(old_data),
                "patterns": self._convert_patterns(old_data),
                "transformations": self._convert_transformations(old_data)
            },
            "validation_knowledge": {
                "criteria": [],
                "checklist": [],
                "error_patterns": self._convert_error_cases(old_data)
            },
            "examples": {
                "input_examples": [],
                "output_examples": [],
                "transformation_examples": []
            },
            "relationships": {
                "related_knowledge_bases": [],
                "dependency_graph": {},
                "cross_references": []
            }
        }
        
        return new_knowledge_base
    
    def _convert_concepts(self, old_data: Dict) -> List[Dict]:
        """转换概念数据"""
        concepts = []
        old_concepts = old_data.get('dfd_concepts', [])
        
        for i, old_concept in enumerate(old_concepts):
            concept_id = f"concept_{i+1:03d}"
            concepts.append({
                "concept_id": concept_id,
                "name": old_concept.get('type', ''),
                "definition": old_concept.get('description', ''),
                "category": "dfd_element",
                "attributes": {
                    "symbol": old_concept.get('symbol', ''),
                    "rules": old_concept.get('rules', [])
                },
                "relationships": []
            })
        
        return concepts
    
    def _convert_rules(self, old_data: Dict) -> List[Dict]:
        """转换规则数据"""
        rules = []
        old_rules = old_data.get('dfd_rules', [])
        
        for i, old_rule in enumerate(old_rules):
            rule_id = f"rule_{i+1:03d}"
            rules.append({
                "rule_id": rule_id,
                "type": old_rule.get('category', 'general'),
                "condition": old_rule.get('condition', ''),
                "action": old_rule.get('description', ''),
                "priority": 1,
                "applicable_scenarios": ["dfd_creation"]
            })
        
        return rules
    
    def _convert_patterns(self, old_data: Dict) -> List[Dict]:
        """转换模式数据"""
        patterns = []
        old_patterns = old_data.get('dfd_patterns', [])
        
        for i, old_pattern in enumerate(old_patterns):
            pattern_id = f"pattern_{i+1:03d}"
            patterns.append({
                "pattern_id": pattern_id,
                "name": old_pattern.get('system', f'模式{i+1}'),
                "template": json.dumps(old_pattern, ensure_ascii=False),
                "variables": {
                    "level": old_pattern.get('level', 0),
                    "processes": old_pattern.get('processes', []),
                    "entities": old_pattern.get('entities', []),
                    "data_stores": old_pattern.get('data_stores', []),
                    "flows": old_pattern.get('flows', [])
                },
                "usage_context": "DFD系统建模",
                "complexity_level": "medium"
            })
        
        return patterns
    
    def _convert_transformations(self, old_data: Dict) -> List[Dict]:
        """转换变换数据"""
        transformations = []
        old_mappings = old_data.get('dfd_nlp_mappings', [])
        
        for i, old_mapping in enumerate(old_mappings):
            transformation_id = f"transform_{i+1:03d}"
            transformations.append({
                "transformation_id": transformation_id,
                "from_format": "natural_language",
                "to_format": "dfd_element",
                "steps": [
                    f"识别模式: {old_mapping.get('pattern', '')}",
                    f"映射到元素类型: {old_mapping.get('element_type', '')}",
                    f"应用命名模板: {old_mapping.get('name_template', '')}"
                ],
                "tools_required": ["nlp_parser", "dfd_generator"],
                "preconditions": ["文本预处理完成"]
            })
        
        return transformations
    
    def _convert_error_cases(self, old_data: Dict) -> List[Dict]:
        """转换错误案例数据"""
        error_patterns = []
        old_cases = old_data.get('dfd_cases', [])
        
        for i, old_case in enumerate(old_cases):
            if old_case.get('type') == 'error':
                error_id = f"error_{i+1:03d}"
                error_patterns.append({
                    "error_id": error_id,
                    "pattern_description": old_case.get('description', ''),
                    "symptoms": [old_case.get('description', '')],
                    "root_causes": [],
                    "solutions": [old_case.get('explanation', '')],
                    "prevention_measures": []
                })
        
        return error_patterns

if __name__ == "__main__":
    processor = UniversalKnowledgeProcessor()
    
    # 测试内容提取
    sample_content = """
    数据流图（DFD）是指描述系统中数据流动的图形化表示方法。
    规则1：每个处理过程必须有输入和输出。
    步骤1：识别外部实体
    步骤2：确定主要处理过程
    步骤3：绘制数据流
    示例：学生注册系统包含学生、注册处理、学生信息存储等元素。
    错误：处理过程没有输入数据流是常见的建模错误。
    """
    
    knowledge_base = processor.extract_knowledge(
        content=sample_content,
        url="https://example.com",
        title="DFD建模指南",
        requirement_type="自然语言需求",
        target_conversion_type="数据流图"
    )
    
    print(json.dumps(knowledge_base, ensure_ascii=False, indent=2))
    
    # 保存知识库
    filepath = processor.save_knowledge_base(knowledge_base)
    print(f"知识库已保存到: {filepath}")

    def _summarize_title_from_definition(self, definition: str) -> str:
        import re
        text = (definition or "").strip()
        if not text:
            return ""
        # 清理常见引导词
        text = re.sub(r'^(关于|本文|这篇|介绍|总结|概述|定义|说明|什么是)\s*', '', text)
        # 选择连接词之前的片段作为主题
        connectors = ['是指', '是', '为', '指', '表示', '属于', '包括', '包含', '主要', '一般']
        pos_candidates = [text.find(c) for c in connectors if c in text]
        pos = min(pos_candidates) if pos_candidates else -1
        if pos != -1 and pos > 0:
            candidate = text[:pos]
        else:
            if '：' in text:
                candidate = text.split('：', 1)[0]
            elif ':' in text:
                candidate = text.split(':', 1)[0]
            else:
                candidate = re.split(r'[，。,、；;！!？?]', text)[0]
        candidate = candidate.strip()
        candidate = self._refine_concept_name(candidate)
        # 若仍不合法，取首句再清理
        if not self._is_valid_concept_name(candidate):
            candidate = re.sub(r'\s+', ' ', re.split(r'[，。,、；;！!？?]', text)[0]).strip()
            candidate = self._refine_concept_name(candidate)
        if candidate and len(candidate) > 18:
            candidate = candidate[:18]
        return candidate

    def _auto_title_if_needed(self, name: str, definition: str) -> str:
        import re
        n = (name or "").strip()
        d = (definition or "").strip()
        if not d:
            return n
        bad_signals = ['包括','包含','一般','主要','可以','需要','用于','通过','以及','比如']
        looks_listy = bool(re.search(r'[，、；;]', n))
        too_long = len(n) > 16
        # 当名称过长、像列表或包含弱标题信号时，生成摘要标题
        if too_long or looks_listy or any(s in n for s in bad_signals):
            summarized = self._summarize_title_from_definition(d)
            if summarized and self._is_valid_concept_name(summarized):
                return summarized
        return n