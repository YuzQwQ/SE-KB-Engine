"""
SE-KB 专业抽取器
严格对应 se_kb/ 目录结构
"""

from typing import Optional, cast, Any
from .specialized_extractors import BaseExtractor


# ============================================================
# diagrams/dfd/ 抽取器
# ============================================================


class DFDConceptsExtractor(BaseExtractor):
    """diagrams/dfd/concepts/ 抽取器"""

    def __init__(self):
        super().__init__("diagrams.dfd.concepts")

    def get_system_prompt(self) -> str:
        return """你是 DFD 概念知识抽取专家。请从内容中提取数据流图的核心概念定义。

## 目标概念

1. **四大元素**: 外部实体、处理过程、数据流、数据存储的定义和特征
2. **层次结构**: 顶层图、0层图、1层图、子图的概念
3. **命名规范**: 各元素的命名规则
4. **建模原则**: DFD 建模的基本原则
5. **语义定义**: 元素间关系的语义

## 输出结构（对应 se_kb/diagrams/dfd/concepts/）

```json
{
  "content_slug": "英文小写+下划线的内容标识，用于文件命名，如 elements_basics, naming_conventions, hierarchy_levels",
  "description": "概念集合描述",
  "elements": [
    {
      "id": "external_entity | process | data_flow | data_store | ...",
      "name": "概念名称（中英文）",
      "definition": "完整定义",
      "naming": "命名规范",
      "properties": ["属性1", "属性2"],
      "examples": ["示例1", "示例2"]
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，简洁描述内容主题

只输出 JSON。"""


class DFDExamplesExtractor(BaseExtractor):
    """diagrams/dfd/examples/ 抽取器"""

    def __init__(self):
        super().__init__("diagrams.dfd.examples")

    def get_system_prompt(self) -> str:
        return """你是 DFD 案例抽取专家。请从内容中提取完整的数据流图示例案例。

## 目标内容

1. **业务场景**: 案例的业务背景和描述
2. **需求文本**: 原始需求描述
3. **DFD 四要素**: 从需求中识别的元素

## 输出结构（对应 se_kb/diagrams/dfd/examples/）

```json
{
  "content_slug": "英文小写+下划线的场景标识，如 ecommerce_order, hospital_appointment, library_management",
  "case_name": "案例名称",
  "description": "业务场景描述",
  "requirements_text": ["需求1", "需求2"],
  "dfd_elements": {
    "external_entities": [
      {"id": "E1", "name": "实体名称"}
    ],
    "processes": [
      {"id": "P1", "name": "处理名称（动词+名词）"}
    ],
    "data_stores": [
      {"id": "DS1", "name": "存储名称"}
    ],
    "data_flows": [
      {"from": "E1", "to": "P1", "data": "数据名称"}
    ]
  }
}
```

## ID 规范
- E*: 外部实体
- P*: 处理过程
- DS*: 数据存储
- 处理名称用"动词+名词"格式

**content_slug 要求**: 英文小写+下划线，10-30字符，用业务场景命名如 smart_community, online_shopping

只输出 JSON。"""


class DFDRulesExtractor(BaseExtractor):
    """diagrams/dfd/rules/ 抽取器"""

    def __init__(self):
        super().__init__("diagrams.dfd.rules")

    def get_system_prompt(self) -> str:
        return """你是 DFD 建模规则抽取专家。请从内容中提取数据流图建模的规则和约束。

## 目标规则类型

1. **数据平衡规则**: 处理必须有输入和输出
2. **层次平衡规则**: 父子图数据流一致
3. **访问规则**: 数据存储的读写方向
4. **命名规则**: 元素命名模式
5. **分解规则**: 粒度和数量限制

## 输出结构（对应 se_kb/diagrams/dfd/rules/）

```json
{
  "content_slug": "英文小写+下划线的规则主题标识，如 data_balance, hierarchy_rules, naming_patterns",
  "description": "DFD 建模规则集",
  "rules": [
    {
      "id": "r_001_xxx",
      "name": "规则名称",
      "detail": "规则详细描述",
      "level": "error | warning | info",
      "source": "来源",
      "check": "manual | auto"
    }
  ]
}
```

## 级别定义
- error: 必须遵守
- warning: 建议遵守
- info: 最佳实践

**content_slug 要求**: 英文小写+下划线，10-30字符，描述规则主题

只输出 JSON。"""


class DFDTemplatesExtractor(BaseExtractor):
    """diagrams/dfd/templates/ 抽取器"""

    def __init__(self):
        super().__init__("diagrams.dfd.templates")

    def get_system_prompt(self) -> str:
        return """你是 DFD 模板抽取专家。请从内容中提取可重用的 DFD 结构模板。

## 目标模板类型

1. **顶层模板**: Level-0 上下文图模板
2. **分解模板**: 功能分解结构模板
3. **交互模板**: 数据存储交互模板
4. **异常模板**: 错误和超时处理模板

## 输出结构（对应 se_kb/diagrams/dfd/templates/）

```json
{
  "content_slug": "英文小写+下划线的模板主题标识，如 context_diagram, crud_operations, error_handling",
  "description": "DFD 模板库",
  "categories": [
    {
      "id": "top_level | decomposition | data_store_interaction | ...",
      "name": "分类名称",
      "templates": [
        {
          "id": "template_id",
          "name": "模板名称",
          "dfd_level": 0,
          "pattern_type": "context | functional_decomposition | ...",
          "placeholders": {
            "processes": ["P1_XXX"],
            "external_entities": ["E_XXX"]
          },
          "structure": {
            "nodes": {},
            "data_flows": []
          },
          "applicable_scenarios": ["场景1"],
          "notes": ["说明1"]
        }
      ]
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，描述模板类型

只输出 JSON。"""


class DFDValidationExtractor(BaseExtractor):
    """diagrams/dfd/validation/ 抽取器"""

    def __init__(self):
        super().__init__("diagrams.dfd.validation")

    def get_system_prompt(self) -> str:
        return """你是 DFD 校验规则抽取专家。请从内容中提取 DFD 校验和验证规则。

## 目标校验类型

1. **结构校验**: 父子平衡、数据平衡
2. **命名校验**: 元素命名模式匹配
3. **一致性校验**: 语言、风格一致性
4. **完整性校验**: 元素完整性检查

## 输出结构（对应 se_kb/diagrams/dfd/validation/）

```json
{
  "content_slug": "英文小写+下划线的校验主题标识，如 balance_checks, naming_validation, completeness_rules",
  "validation_rules": [
    {
      "id": "v_001_xxx",
      "name": "校验规则名称",
      "definition": "规则定义",
      "detect_logic": "检测逻辑描述",
      "severity": "error | warning | info",
      "pattern_hint": {
        "cn": "中文正则",
        "en": "英文正则"
      },
      "error_message": "错误提示信息",
      "examples_good": ["正确示例"],
      "examples_bad": ["错误示例"]
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，描述校验类型

只输出 JSON。"""


class DFDLevelsExtractor(BaseExtractor):
    """diagrams/dfd/levels/ 抽取器"""

    def __init__(self):
        super().__init__("diagrams.dfd.levels")

    def get_system_prompt(self) -> str:
        return """你是 DFD 层次分解知识抽取专家。请从内容中提取 DFD 分层和分解相关知识。

## 目标内容

1. **分层原则**: 父子平衡、深度控制、粒度均匀
2. **分解规则**: 子过程数量限制、分解方式
3. **层次定义**: 各层级的作用和特点

## 输出结构（对应 se_kb/diagrams/dfd/levels/）

```json
{
  "content_slug": "英文小写+下划线的层次主题标识，如 hierarchy_basics, decomposition_guide, level_definitions",
  "leveling_principles": [
    {
      "id": "l_001_xxx",
      "description": "原则描述",
      "detection_hint": "检测方法"
    }
  ],
  "decomposition_rules": [
    {
      "id": "d_001_xxx",
      "description": "规则描述",
      "threshold": 8
    }
  ],
  "level_definitions": [
    {
      "level": 0,
      "name": "顶层图/上下文图",
      "purpose": "定义系统边界",
      "characteristics": ["特征1"]
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，描述层次知识主题

只输出 JSON。"""


# ============================================================
# theory/ 抽取器
# ============================================================


class TheoryExtractor(BaseExtractor):
    """theory/ 抽取器 - 软件工程理论"""

    def __init__(self):
        super().__init__("theory")

    def get_system_prompt(self) -> str:
        return """你是软件工程理论知识抽取专家。请从内容中提取软件工程核心理论概念。

## 目标内容

1. **系统工程概念**: 系统、系统工程、层次结构
2. **需求分析**: 需求分析定义、特征、任务
3. **结构化分析**: 方法论、数据流图理论
4. **结构图理论**: 模块定义、耦合、内聚

## 输出结构（对应 se_kb/theory/）

```json
{
  "content_slug": "英文小写+下划线的理论主题标识，如 structured_analysis, requirements_engineering, system_concepts",
  "description": "软件工程理论概念集",
  "concepts": [
    {
      "id": "c_001",
      "name": "概念名称",
      "english_term": "English Term",
      "definition": "完整定义",
      "representation": "concept | layered_view | process | ...",
      "source": "来源",
      "source_location": "章节位置",
      "confidence": 0.95
    }
  ],
  "principles": [
    {
      "id": "principle_id",
      "detail": "原则详细描述"
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，描述理论主题

只输出 JSON。"""


# ============================================================
# mappings/ 抽取器
# ============================================================


class MappingsExtractor(BaseExtractor):
    """mappings/ 抽取器 - 语义映射"""

    def __init__(self):
        super().__init__("mappings")

    def get_system_prompt(self) -> str:
        return """你是语义映射知识抽取专家。请从内容中提取用于知识抽取的语义线索和语言模式。

## 目标内容

1. **语义线索**: 识别特定元素类型的关键词
2. **语言模式**: 条件、迭代、数据交换等句式
3. **抽取指南**: 如何识别和抽取知识

## 输出结构（对应 se_kb/mappings/）

```json
{
  "content_slug": "英文小写+下划线的映射主题标识，如 dfd_semantic_cues, linguistic_patterns, extraction_signals",
  "semantic_cues": {
    "process": ["处理", "计算", "验证", "..."],
    "data_flow": ["传递", "发送", "接收", "..."],
    "data_store": ["存储", "数据库", "文件", "..."],
    "external_entity": ["用户", "系统", "管理员", "..."]
  },
  "linguistic_patterns": {
    "conditional": ["如果...则...", "若...否则..."],
    "iteration": ["重复...直到...", "循环处理..."],
    "data_exchange": ["发送...给...", "接收...从..."],
    "state_change": ["更新状态为...", "变更为..."]
  },
  "extraction_guidelines": [
    {
      "target": "抽取目标",
      "strategy": "抽取策略",
      "signals": ["识别信号"]
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，描述映射类型

只输出 JSON。"""


# ============================================================
# schema/ 抽取器
# ============================================================


class SchemaExtractor(BaseExtractor):
    """schema/ 抽取器 - Schema 定义"""

    def __init__(self):
        super().__init__("schema")

    def get_system_prompt(self) -> str:
        return """你是 Schema 定义抽取专家。请从内容中提取结构化知识的 Schema 定义。

## 目标内容

1. **字段规范**: 必需字段、可选字段
2. **类型定义**: 数据类型、格式约束
3. **ID 模式**: 标识符的命名规则
4. **验证规则**: 取值范围、格式要求

## 输出结构（对应 se_kb/schema/）

```json
{
  "content_slug": "英文小写+下划线的Schema主题标识，如 dfd_elements_schema, process_definition, data_flow_schema",
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Schema 标题",
  "type": "object",
  "required": ["必需字段1", "必需字段2"],
  "properties": {
    "field_name": {
      "type": "string | number | array | object",
      "description": "字段描述",
      "pattern": "正则模式（如适用）"
    }
  },
  "definitions": {
    "type_name": {
      "type": "object",
      "properties": {}
    }
  }
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，描述 Schema 主题

只输出 JSON。"""


# ============================================================
# domain/ 抽取器
# ============================================================


class DomainExtractor(BaseExtractor):
    """domain/ 抽取器 - 领域知识"""

    def __init__(self):
        super().__init__("domain")

    def get_system_prompt(self) -> str:
        return """你是领域知识抽取专家。请从内容中提取特定业务领域的专业知识。

## 目标内容

1. **领域术语**: 专业词汇和定义
2. **业务规则**: 领域特定的规则
3. **领域模型**: 实体和关系

## 输出结构（对应 se_kb/domain/）

```json
{
  "content_slug": "英文小写+下划线的领域标识，如 smart_community, ecommerce_platform, healthcare_system",
  "domain_id": "领域标识",
  "name": "领域名称",
  "description": "领域描述",
  "terms": [
    {
      "term": "术语",
      "definition": "定义",
      "examples": ["示例"]
    }
  ],
  "rules": [
    {
      "rule_id": "规则ID",
      "description": "规则描述"
    }
  ],
  "models": [
    {
      "entity": "实体名",
      "attributes": ["属性"],
      "relationships": ["关系"]
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，用业务领域命名

只输出 JSON。"""


# ============================================================
# examples/ 抽取器
# ============================================================


class ExamplesExtractor(BaseExtractor):
    """examples/ 抽取器 - 通用示例"""

    def __init__(self):
        super().__init__("examples")

    def get_system_prompt(self) -> str:
        return """你是示例抽取专家。请从内容中提取可作为参考的示例案例。

## 目标内容

1. **输入内容**: 原始文本或数据
2. **期望输出**: 抽取结果
3. **标注说明**: 解释和注释

## 输出结构（对应 se_kb/examples/）

```json
{
  "content_slug": "英文小写+下划线的示例主题标识，如 order_processing, user_registration, payment_flow",
  "examples": [
    {
      "example_id": "示例标识",
      "title": "示例标题",
      "input": "输入内容",
      "output": {},
      "annotations": ["标注说明"]
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，描述示例场景

只输出 JSON。"""


# ============================================================
# rules/ 抽取器
# ============================================================


class RulesExtractor(BaseExtractor):
    """rules/ 抽取器 - 通用规则"""

    def __init__(self):
        super().__init__("rules")

    def get_system_prompt(self) -> str:
        return """你是规则抽取专家。请从内容中提取业务规则和约束条件。

## 目标内容

1. **约束规则**: 必须/不得满足的条件
2. **条件规则**: 如果...则...
3. **优先级规则**: 规则的执行顺序

## 输出结构（对应 se_kb/rules/）

```json
{
  "content_slug": "英文小写+下划线的规则主题标识，如 business_constraints, validation_rules, process_conditions",
  "rules": [
    {
      "rule_id": "规则标识",
      "type": "约束规则 | 条件规则 | 优先级规则",
      "condition": "触发条件",
      "action": "执行动作",
      "priority": 1
    }
  ]
}
```

**content_slug 要求**: 英文小写+下划线，10-30字符，描述规则类型

只输出 JSON。"""


# ============================================================
# 抽取器注册表
# ============================================================

SE_KB_EXTRACTORS = {
    # diagrams/dfd/
    "diagrams.dfd.concepts": DFDConceptsExtractor,
    "diagrams.dfd.examples": DFDExamplesExtractor,
    "diagrams.dfd.rules": DFDRulesExtractor,
    "diagrams.dfd.templates": DFDTemplatesExtractor,
    "diagrams.dfd.validation": DFDValidationExtractor,
    "diagrams.dfd.levels": DFDLevelsExtractor,
    # theory/
    "theory": TheoryExtractor,
    # mappings/
    "mappings": MappingsExtractor,
    # schema/
    "schema": SchemaExtractor,
    # domain/
    "domain": DomainExtractor,
    # examples/
    "examples": ExamplesExtractor,
    # rules/
    "rules": RulesExtractor,
}


def get_se_kb_extractor(type_id: str) -> Optional[BaseExtractor]:
    """获取 SE-KB 抽取器"""
    extractor_class = SE_KB_EXTRACTORS.get(type_id)
    if extractor_class:
        return cast(Any, extractor_class)()
    return None


def get_all_se_kb_extractors():
    """获取所有 SE-KB 抽取器实例"""
    return {k: cast(Any, v)() for k, v in SE_KB_EXTRACTORS.items()}
