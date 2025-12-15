"""
Specialized Extractors - 专业抽取器 (Stage 2)
每种知识类型有独立的专用抽取器，使用专属 prompt 进行结构化抽取
"""

import os
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass

from .type_registry import get_type_registry, KnowledgeType


# ============================================================
# 模型分级配置
# 简单类型用小模型（降本），复杂类型用大模型（保质量）
# 
# 可通过环境变量覆盖：
#   KB_MODEL_ID       - 统一使用的模型（优先级最高，覆盖分级）
#   KB_MODEL_SIMPLE   - 简单类型用的模型
#   KB_MODEL_COMPLEX  - 复杂类型用的模型
#   KB_MODEL_DEFAULT  - 默认模型
# ============================================================

# 简单类型：概念定义、层次说明等（结构固定，内容简单）
SIMPLE_TYPES = {
    "diagrams.dfd.concepts",
    "diagrams.dfd.levels",
    "diagrams.dfd.rules",
    "diagrams.dfd.validation",
    "theory",
    "mappings",
    "rules",
}

# 复杂类型：示例、模板、领域知识（需要理解和生成）
COMPLEX_TYPES = {
    "diagrams.dfd.examples",
    "diagrams.dfd.templates",
    "schema",
    "domain",
    "examples",
}


@dataclass
class ExtractionResult:
    """抽取结果"""
    artifact: Optional[Dict[str, Any]]  # 结构化输出
    success: bool                        # 是否成功
    error: Optional[str]                 # 错误信息
    tokens_used: int                     # 消耗的 tokens


class BaseExtractor(ABC):
    """抽取器基类"""
    
    def __init__(self, type_id: str):
        self.type_id = type_id
        self._load_env()
        self.base_url = os.getenv('KB_BASE_URL', '').rstrip('/')
        self.api_key = os.getenv('KB_API_KEY', '')
        # 根据类型选择模型
        self.model_id = self._select_model(type_id)
        self.timeout = 90.0
        self.registry = get_type_registry()
        self.knowledge_type = self.registry.get(type_id)
    
    def _select_model(self, type_id: str) -> str:
        """
        根据知识类型选择合适的模型
        
        优先级：
        1. KB_MODEL_ID - 统一模型（最高优先级，禁用分级）
        2. KB_MODEL_SIMPLE / KB_MODEL_COMPLEX - 分级模型
        3. KB_MODEL_DEFAULT - 默认模型
        """
        # 如果设置了统一模型，直接使用（禁用分级）
        unified_model = os.getenv('KB_MODEL_ID')
        if unified_model:
            return unified_model
        
        # 获取分级模型配置
        model_simple = os.getenv('KB_MODEL_SIMPLE')
        model_complex = os.getenv('KB_MODEL_COMPLEX')
        model_default = os.getenv('KB_MODEL_DEFAULT', 'Qwen/Qwen2.5-72B-Instruct')
        
        # 根据类型选择模型
        if type_id in SIMPLE_TYPES and model_simple:
            return model_simple
        elif type_id in COMPLEX_TYPES and model_complex:
            return model_complex
        else:
            return model_default
    
    def _load_env(self):
        """加载环境变量"""
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
    
    def _load_schema(self) -> str:
        """加载 JSON Schema"""
        if not self.knowledge_type or not self.knowledge_type.schema_path:
            return "{}"
        try:
            return Path(self.knowledge_type.schema_path).read_text(encoding='utf-8')
        except Exception:
            return "{}"
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取专用系统提示词（子类实现）"""
        pass
    
    def _build_user_prompt(self, content: str, ctx: Dict[str, Any]) -> str:
        """构建用户提示词"""
        return f"""请从以下内容中抽取 {self.knowledge_type.name if self.knowledge_type else self.type_id} 相关的结构化知识。

## 来源信息
- 标题: {ctx.get('title', '未知')}
- URL: {ctx.get('url', '')}

## 内容

{content}

---

请严格按照系统提示词中的 Schema 和要求输出 JSON。"""
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[str], Dict]:
        """调用大模型"""
        if not self.base_url or not self.api_key:
            return None, {"error": "missing_env", "need": ["KB_BASE_URL", "KB_API_KEY"]}
        
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
                'temperature': 0,
                'max_tokens': 4096,
                'response_format': {'type': 'json_object'},
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                content = ((data.get('choices') or [{}])[0].get('message') or {}).get('content', '')
                tokens = data.get('usage', {}).get('total_tokens', 0)
                return content, {"tokens": tokens, "model": self.model_id}
        
        except Exception as e:
            return None, {"error": str(e)}
    
    def _parse_json(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 JSON 响应"""
        if not response:
            return None
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def extract(self, content: str, ctx: Dict[str, Any]) -> Tuple[ExtractionResult, Dict[str, Any]]:
        """
        执行抽取
        
        Args:
            content: 待抽取的文本内容
            ctx: 上下文信息 (title, url 等)
        
        Returns:
            (ExtractionResult, trace)
        """
        system_prompt = self.get_system_prompt()
        user_prompt = self._build_user_prompt(content, ctx)
        
        response, trace = self._call_llm(system_prompt, user_prompt)
        
        if not response:
            return ExtractionResult(None, False, trace.get('error', 'LLM调用失败'), 0), trace
        
        artifact = self._parse_json(response)
        
        if artifact is None:
            return ExtractionResult(None, False, "JSON解析失败", trace.get('tokens', 0)), trace
        
        trace['type_id'] = self.type_id
        
        return ExtractionResult(artifact, True, None, trace.get('tokens', 0)), trace


class DFDExtractor(BaseExtractor):
    """DFD 专业抽取器"""
    
    def __init__(self):
        super().__init__('dfd')
    
    def get_system_prompt(self) -> str:
        schema = self._load_schema()
        return f"""你是数据流图(DFD)结构化抽取专家。请从给定内容中提取完整的 DFD 结构。

## DFD 核心元素

1. **外部实体 (External Entity)**: 系统边界外的数据源/接收者
   - ID格式: E1, E2, E3...
   - 命名: 使用角色名词，如"用户"、"管理员"、"第三方系统"

2. **处理过程 (Process)**: 数据变换的功能单元
   - ID格式: P1, P2, P1.1, P1.2...（支持层次编号）
   - 命名: "动词+名词"，如"验证密码"、"处理订单"
   - 必须有输入和输出

3. **数据流 (Data Flow)**: 数据的流动
   - ID格式: F1, F2, F3...
   - 命名: 描述数据内容，如"用户请求"、"验证结果"
   - source/target 引用其他元素的 ID

4. **数据存储 (Data Store)**: 持久化数据
   - ID格式: DS1, DS2, DS3...
   - 命名: 使用名词，如"用户数据库"、"订单表"

## 抽取规则

1. 从文本描述中识别 DFD 四要素
2. 建立元素间的连接关系（数据流）
3. 确保每个 Process 至少有一个输入和一个输出
4. 数据流的 source/target 必须引用有效的元素 ID
5. 如果内容描述了多个层次，标注 level

## JSON Schema（严格遵守）

{schema}

## 输出要求

1. 只输出 JSON，不要任何解释
2. 所有 ID 必须符合 Schema 中的 pattern
3. 如果无法提取完整 DFD，尽量提取能识别的元素
4. 中文命名优先"""


class ConceptsExtractor(BaseExtractor):
    """概念定义专业抽取器"""
    
    def __init__(self):
        super().__init__('concepts')
    
    def get_system_prompt(self) -> str:
        return """你是概念定义结构化抽取专家。请从给定内容中提取专业概念和定义。

## 识别特征

- 定义句式："X是指..."、"所谓X..."、"X定义为..."、"X表示..."、"X即..."
- 概念分类和属性描述
- 概念间的关系说明

## 输出结构

```json
{
  "generation_knowledge": {
    "concepts": [
      {
        "concept_id": "concept_001",
        "name": "简洁的概念名称（10-25字符）",
        "definition": "完整的定义说明（包含上下文和详细解释）",
        "category": "分类",
        "attributes": {"key": "value"},
        "relationships": ["relates_to: 其他概念"]
      }
    ]
  }
}
```

## 抽取规则

1. name 字段必须是简洁的主题短语，不能直接截取 definition
2. definition 必须是完整的解释，包含足够上下文
3. 每个概念必须有实际意义，不要提取过于泛化的内容
4. 优先提取专业术语和核心概念
5. 最少提取 3 个概念，最多 15 个

## 输出要求

只输出 JSON，不要任何解释。"""


class RulesExtractor(BaseExtractor):
    """规则约束专业抽取器"""
    
    def __init__(self):
        super().__init__('rules')
    
    def get_system_prompt(self) -> str:
        return """你是规则约束结构化抽取专家。请从给定内容中提取业务规则和约束条件。

## 识别特征

- 强制规则："必须..."、"应当..."、"不得..."、"禁止..."
- 条件规则："如果...则..."、"当...时..."、"若...则..."
- 约束描述："限制..."、"约束..."、"要求..."
- 规范要求："规范..."、"标准..."、"应该..."

## 输出结构

```json
{
  "generation_knowledge": {
    "rules": [
      {
        "rule_id": "rule_001",
        "type": "约束规则|条件规则|规范规则|命名规则",
        "condition": "触发条件（如果有）",
        "action": "规则内容或要求",
        "priority": 1,
        "applicable_scenarios": ["适用场景1", "适用场景2"]
      }
    ]
  }
}
```

## 抽取规则

1. 区分规则类型：约束、条件、规范、命名等
2. condition 描述触发条件，action 描述具体要求
3. priority 1-5，1 最高
4. 最少提取 3 条规则，最多 12 条
5. 只提取明确的规则，不要推测

## 输出要求

只输出 JSON，不要任何解释。"""


class PatternsExtractor(BaseExtractor):
    """模式模板专业抽取器"""
    
    def __init__(self):
        super().__init__('patterns')
    
    def get_system_prompt(self) -> str:
        return """你是模式模板结构化抽取专家。请从给定内容中提取可重用的模式和模板。

## 识别特征

- 模板结构：固定格式 + 可变参数
- 设计模式：经过验证的解决方案
- 格式规范：标准化的文档/代码格式
- 流程模板：标准化的工作流程

## 输出结构

```json
{
  "generation_knowledge": {
    "patterns": [
      {
        "pattern_id": "pattern_001",
        "name": "模式名称",
        "template": "模板内容或结构描述",
        "variables": {"var1": "说明", "var2": "说明"},
        "usage_context": "使用场景",
        "complexity_level": "simple|moderate|complex"
      }
    ]
  }
}
```

## 输出要求

只输出 JSON，不要任何解释。"""


class TransformationsExtractor(BaseExtractor):
    """转换方法专业抽取器"""
    
    def __init__(self):
        super().__init__('transformations')
    
    def get_system_prompt(self) -> str:
        return """你是转换方法结构化抽取专家。请从给定内容中提取格式转换和方法步骤。

## 识别特征

- 步骤描述："第一步..."、"然后..."、"最后..."
- 转换关系："从...到..."、"转换为..."、"映射..."
- 方法说明："方法..."、"技术..."、"过程..."

## 输出结构

```json
{
  "generation_knowledge": {
    "transformations": [
      {
        "transformation_id": "trans_001",
        "name": "转换名称",
        "from_format": "输入格式/表示",
        "to_format": "输出格式/表示",
        "steps": ["步骤1", "步骤2", "步骤3"],
        "tools_required": ["工具1"],
        "preconditions": ["前置条件"]
      }
    ]
  }
}
```

## 输出要求

只输出 JSON，不要任何解释。"""


class ValidationExtractor(BaseExtractor):
    """验证标准专业抽取器"""
    
    def __init__(self):
        super().__init__('validation')
    
    def get_system_prompt(self) -> str:
        return """你是验证标准结构化抽取专家。请从给定内容中提取验证标准、检查清单和错误模式。

## 输出结构

```json
{
  "validation_knowledge": {
    "criteria": [
      {
        "criteria_id": "criteria_001",
        "name": "标准名称",
        "description": "标准描述",
        "measurement_method": "度量方法",
        "threshold_values": {"key": "value"},
        "weight": 1.0
      }
    ],
    "checklist": [
      {
        "check_id": "check_001",
        "category": "分类",
        "description": "检查项描述",
        "validation_method": "验证方法",
        "expected_result": "期望结果",
        "severity_level": "high|medium|low"
      }
    ],
    "error_patterns": [
      {
        "error_id": "error_001",
        "pattern_description": "错误模式描述",
        "symptoms": ["症状1"],
        "root_causes": ["根因1"],
        "solutions": ["解决方案1"],
        "prevention_measures": ["预防措施1"]
      }
    ]
  }
}
```

## 输出要求

只输出 JSON，不要任何解释。"""


# 旧抽取器注册表（保留用于兼容）
LEGACY_EXTRACTORS = {
    'dfd': DFDExtractor,
    'concepts': ConceptsExtractor,
    'rules': RulesExtractor,
    'patterns': PatternsExtractor,
    'transformations': TransformationsExtractor,
    'validation': ValidationExtractor,
}


def get_extractor(type_id: str) -> Optional[BaseExtractor]:
    """
    获取指定类型的抽取器
    优先使用 SE-KB 抽取器，回退到旧版抽取器
    """
    # 1. 优先使用 SE-KB 抽取器
    try:
        from .se_kb_extractors import get_se_kb_extractor
        extractor = get_se_kb_extractor(type_id)
        if extractor:
            return extractor
    except ImportError:
        pass
    
    # 2. 回退到旧版抽取器
    extractor_class = LEGACY_EXTRACTORS.get(type_id)
    if extractor_class:
        return extractor_class()
    
    return None


def extract_by_type(type_id: str, content: str, ctx: Dict[str, Any]) -> Tuple[ExtractionResult, Dict[str, Any]]:
    """
    便捷函数：按类型抽取
    
    Args:
        type_id: 知识类型
        content: 待抽取内容
        ctx: 上下文
    
    Returns:
        (ExtractionResult, trace)
    """
    extractor = get_extractor(type_id)
    if not extractor:
        return ExtractionResult(None, False, f"未知类型: {type_id}", 0), {"error": "unknown_type"}
    
    return extractor.extract(content, ctx)

