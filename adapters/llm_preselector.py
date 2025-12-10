"""
LLM Preselector - 使用小模型进行候选片段筛选
替代原有的关键词规则过滤，实现高召回率的语义级候选提取
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

@dataclass
class CandidateChunk:
    """候选片段"""
    text: str
    type: str  # dfd, concept, rule, unknown
    confidence: float = 0.0
    source_section: str = ""  # 来源章节标题
    context_before: str = ""  # 上文摘要
    context_after: str = ""   # 下文摘要


PRESELECTOR_SYSTEM_PROMPT = """你是一个专业的软件工程知识筛选器，专门从网页内容中识别和提取与"数据流图(DFD)"、"概念定义"、"规则约束"相关的段落。

## 你的任务
从给定的网页内容中，找出所有可能包含以下三类知识的段落：

### 1. DFD（数据流图）相关内容 → type="dfd"
识别特征：
- 描述数据流图的四种基本元素：外部实体(External Entity)、处理/加工(Process)、数据流(Data Flow)、数据存储(Data Store)
- 提到 DFD 的层次结构：顶层图、0层图、1层图、子图分解
- 描述数据如何在系统中流动、被处理、被存储
- 包含具体的 DFD 示例：如"用户→登录处理→用户表"这样的流向描述
- 提到符号规范：圆形/圆角矩形表示处理、箭头表示数据流、开口矩形表示数据存储、正方形表示外部实体
- 包含具体的处理过程描述，如"接收订单"、"验证用户"、"更新库存"等
- 描述输入输出关系、数据变换过程

### 2. 概念定义 → type="concept"
识别特征：
- 句式："X是指..."、"X定义为..."、"所谓X..."、"X表示..."、"X即..."
- 对专业术语的解释和说明
- 概念的分类、属性、特征描述
- 概念之间的关系说明（如"A包含B"、"A是B的一种"）
- 学术性或标准性的定义陈述

### 3. 规则约束 → type="rule"
识别特征：
- 句式："必须..."、"应当..."、"不得..."、"如果...则..."、"当...时..."
- 描述约束条件、限制、前提条件
- 描述操作规范、命名规范、设计规范
- 描述因果关系和条件判断
- 最佳实践、注意事项、警告提示

### 4. 无法判断 → type="unknown"
- 内容可能相关但特征不明显
- 需要更多上下文才能确定
- 过于笼统的描述

## 输出要求

1. **高召回率优先**：宁可多选，不要漏选。如果一个段落可能相关，就选入。
2. **段落完整性**：不要截断语义完整的段落，保持上下文连贯。
3. **最小长度**：每个候选段落至少50个字符，避免过于碎片化。
4. **合并相邻段落**：如果连续的短段落讨论同一主题，合并为一个候选。
5. **保留列表内容**：如果列表项与主题相关，保留完整列表。
6. **保留示例**：DFD 相关的示例描述非常重要，必须保留。

## 输出格式

严格输出 JSON 数组，不要有任何其他内容：
```json
[
  {
    "text": "段落原文（完整保留，不要修改）",
    "type": "dfd|concept|rule|unknown",
    "reason": "简短说明为什么选择这个类型（10-30字）"
  }
]
```

如果网页内容与这三类知识完全无关，输出空数组：[]
"""

PRESELECTOR_USER_PROMPT_TEMPLATE = """请从以下网页内容中筛选候选段落。

## 网页信息
- 标题：{title}
- URL：{url}

## 网页正文

{content}

---

请按照系统提示的要求，输出 JSON 数组。记住：高召回率优先，不要遗漏可能相关的内容。"""


class LLMPreselector:
    """基于 LLM 的候选片段预筛选器"""
    
    def __init__(self):
        self._load_env()
        self.base_url = os.getenv('FILTER_BASE_URL', '').rstrip('/')
        self.api_key = os.getenv('FILTER_API_KEY', '')
        self.model_id = os.getenv('FILTER_MODEL_ID', 'Qwen/Qwen2.5-7B-Instruct')
        self.max_input_chars = 12000  # 小模型上下文限制，预留输出空间
        self.timeout = 60.0
    
    def _load_env(self):
        """加载 .env 文件"""
        env_path = Path('.env')
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding='utf-8').splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        k, v = k.strip(), v.strip()
                        if k and v and os.getenv(k) is None:
                            os.environ[k] = v
            except Exception:
                pass
    
    def _prepare_content(self, text: str, sections: List[Dict] = None) -> str:
        """
        准备输入内容，优先使用结构化的 sections，否则使用 clean_text
        """
        if sections and len(sections) > 0:
            # 使用结构化的 sections，保留标题层次
            parts = []
            for sec in sections:
                heading = sec.get('heading', '')
                level = sec.get('level', 2)
                sec_text = sec.get('text', '')
                lists = sec.get('lists', [])
                
                # 构建章节文本
                if heading:
                    parts.append(f"{'#' * level} {heading}")
                if sec_text:
                    parts.append(sec_text)
                if lists:
                    for item in lists:
                        parts.append(f"- {item}")
                parts.append("")  # 空行分隔
            
            content = "\n".join(parts)
        else:
            content = text or ""
        
        # 截断过长内容
        if len(content) > self.max_input_chars:
            content = content[:self.max_input_chars] + "\n\n[...内容已截断...]"
        
        return content
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[str], Dict]:
        """调用 LLM API"""
        if not self.base_url or not self.api_key:
            return None, {"error": "missing_filter_env", "need": ["FILTER_BASE_URL", "FILTER_API_KEY"]}
        
        try:
            import httpx
            url = f"{self.base_url}/chat/completions"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            body = {
                'model': self.model_id,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'temperature': 0.1,  # 低温度保证一致性
                'max_tokens': 4096,
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                content = ((data.get('choices') or [{}])[0].get('message') or {}).get('content', '')
                trace = {
                    "provider": "siliconflow",
                    "model": self.model_id,
                    "tokens": data.get('usage'),
                    "status": "success"
                }
                return content, trace
        
        except Exception as e:
            return None, {"error": "llm_request_failed", "detail": str(e)}
    
    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 响应，提取 JSON 数组"""
        if not response:
            return []
        
        # 尝试直接解析
        try:
            result = json.loads(response)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\[\s*\{[\s\S]*\}\s*\]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    result = json.loads(json_str)
                    if isinstance(result, list):
                        return result
                except (json.JSONDecodeError, IndexError):
                    continue
        
        return []
    
    def preselect(self, parsed_data: Dict[str, Any]) -> Tuple[List[CandidateChunk], Dict[str, Any]]:
        """
        对 parsed.json 数据进行预筛选
        
        Args:
            parsed_data: 包含 clean_text, sections, title, url 等字段的字典
        
        Returns:
            (candidates, trace): 候选片段列表和追踪信息
        """
        title = parsed_data.get('title', '未命名')
        url = parsed_data.get('source_url') or parsed_data.get('url', '')
        sections = parsed_data.get('sections') or parsed_data.get('structured_json') or []
        clean_text = parsed_data.get('clean_text') or parsed_data.get('markdown') or ''
        
        # 准备内容
        content = self._prepare_content(clean_text, sections)
        
        if not content.strip():
            return [], {"error": "empty_content"}
        
        # 构建提示词
        user_prompt = PRESELECTOR_USER_PROMPT_TEMPLATE.format(
            title=title,
            url=url,
            content=content
        )
        
        # 调用 LLM
        response, trace = self._call_llm(PRESELECTOR_SYSTEM_PROMPT, user_prompt)
        
        if not response:
            return [], trace
        
        # 解析响应
        raw_candidates = self._parse_response(response)
        trace["raw_candidates_count"] = len(raw_candidates)
        
        # 转换为 CandidateChunk
        candidates = []
        for item in raw_candidates:
            if not isinstance(item, dict):
                continue
            text = item.get('text', '').strip()
            ctype = item.get('type', 'unknown').lower()
            
            # 验证类型
            if ctype not in ('dfd', 'concept', 'rule', 'unknown'):
                ctype = 'unknown'
            
            # 过滤过短的片段
            if len(text) < 30:
                continue
            
            candidates.append(CandidateChunk(
                text=text,
                type=ctype,
                confidence=0.8 if ctype != 'unknown' else 0.5
            ))
        
        trace["valid_candidates_count"] = len(candidates)
        
        return candidates, trace
    
    def preselect_by_type(self, parsed_data: Dict[str, Any], target_type: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any], float]:
        """
        按类型筛选候选，返回兼容原 adapter 接口的格式
        
        Args:
            parsed_data: parsed.json 数据
            target_type: 目标类型 (dfd, concepts, rules)
        
        Returns:
            (candidates, trace, score): 候选列表、追踪信息、得分
        """
        all_candidates, trace = self.preselect(parsed_data)
        
        # 类型映射
        type_map = {
            'dfd': 'dfd',
            'concepts': 'concept',
            'rules': 'rule',
        }
        target = type_map.get(target_type, target_type)
        
        # 筛选目标类型（包括 unknown）
        filtered = []
        for c in all_candidates:
            if c.type == target or c.type == 'unknown':
                filtered.append({
                    "text": c.text,
                    "type": c.type,
                    "confidence": c.confidence
                })
        
        # 计算得分
        exact_match = sum(1 for c in all_candidates if c.type == target)
        score = min(1.0, exact_match / 5.0) if exact_match > 0 else 0.1
        
        trace["target_type"] = target_type
        trace["filtered_count"] = len(filtered)
        trace["exact_match_count"] = exact_match
        
        return filtered, trace, score


# 便捷函数
_preselector_instance = None

def get_preselector() -> LLMPreselector:
    """获取单例 preselector"""
    global _preselector_instance
    if _preselector_instance is None:
        _preselector_instance = LLMPreselector()
    return _preselector_instance


def preselect_candidates(parsed_data: Dict[str, Any], target_type: str = None) -> Tuple[List[Dict], Dict, float]:
    """
    便捷函数：预筛选候选片段
    
    Args:
        parsed_data: parsed.json 数据
        target_type: 可选，指定目标类型 (dfd, concepts, rules)
    
    Returns:
        (candidates, trace, score)
    """
    preselector = get_preselector()
    if target_type:
        return preselector.preselect_by_type(parsed_data, target_type)
    else:
        candidates, trace = preselector.preselect(parsed_data)
        return [{"text": c.text, "type": c.type} for c in candidates], trace, 0.5

