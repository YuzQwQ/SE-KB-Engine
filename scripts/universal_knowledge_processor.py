import json
import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid
import string

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
                # 提取概念名称（通常在关键词前面）
                concept_name = "未知概念"
                for keyword in all_indicators:
                    if keyword in sentence:
                        parts = sentence.split(keyword)
                        if len(parts) > 0 and len(parts[0].strip()) > 0:
                            concept_name = parts[0].strip()[:30]  # 限制长度
                        break
                
                concept_id = f"concept_{len(concepts) + 1:03d}"
                concepts.append({
                    "concept_id": concept_id,
                    "name": concept_name,
                    "definition": sentence,
                    "category": "extracted",
                    "attributes": {},
                    "relationships": []
                })
        
        return concepts[:8]  # 限制返回数量
    
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
            # 保留包含中文或有意义英文的句子
            if any('\u4e00' <= c <= '\u9fff' for c in sentence) or (len(sentence) > 20 and any(c.isalpha() for c in sentence)):
                meaningful_sentences.append(sentence)
        
        if len(meaningful_sentences) < 2:
            return []
        
        patterns = []
        config_patterns = self.extraction_config.get('patterns', {})
        template_indicators = config_patterns.get('template_indicators', [])
        
        # 添加更多模式关键词
        pattern_keywords = ['模式', '模板', '格式', '结构', '框架', '样式', '方法', '流程', '步骤']
        all_indicators = template_indicators + pattern_keywords
        
        # 查找模板模式
        for sentence in meaningful_sentences[:8]:  # 限制处理数量
            if any(indicator in sentence for indicator in all_indicators) and len(sentence) > 20:
                # 提取模式名称
                pattern_name = "未知模式"
                for indicator in all_indicators:
                    if indicator in sentence:
                        parts = sentence.split(indicator)
                        if len(parts) > 0 and len(parts[0].strip()) > 0:
                            pattern_name = parts[0].strip()[:30]  # 限制长度
                        break
                
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
        """清理内容，移除JSON格式残留和特殊字符"""
        # 首先尝试提取有意义的文本内容
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
            # 跳过URL行
            if line.startswith('http') or 'www.' in line:
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
        
        # 查找列表项模式
        list_patterns = [r'\d+[.、]\s*([^\n]+)', r'[•·-]\s*([^\n]+)']
        
        for pattern in list_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                check_id = f"check_{len(checklist) + 1:03d}"
                checklist.append({
                    "check_id": check_id,
                    "category": "general",
                    "description": match.strip(),
                    "validation_method": "manual",
                    "expected_result": "符合要求",
                    "severity_level": "medium"
                })
        
        return checklist
    
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
    
    def save_knowledge_base(self, knowledge_base: Dict, output_dir: str = "shared_data/knowledge_base") -> str:
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