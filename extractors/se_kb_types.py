"""
SE-KB 知识类型定义
严格对应 se_kb/ 目录结构
"""

from .type_registry import KnowledgeType

# ============================================================
# SE-KB 知识类型 - 严格对应目录结构
# ============================================================

SE_KB_TYPES = [
    # ========================================================
    # diagrams/dfd/ - 数据流图相关
    # ========================================================
    
    # diagrams/dfd/concepts/
    KnowledgeType(
        type_id="diagrams.dfd.concepts",
        name="DFD 概念定义",
        brief="数据流图的核心概念：外部实体、处理过程、数据流、数据存储的定义，以及命名规范、层次结构、建模原则",
        description='''对应目录: se_kb/diagrams/dfd/concepts/
包含文件: elements.json, hierarchy.json, naming_guidelines.json, semantics.json, 
         modelling_principles.json, id_conventions.json, data_dictionary.json 等
内容结构:
- id: 概念标识
- name: 概念名称（中英文）
- definition: 完整定义
- naming: 命名规范
- properties: 属性列表
- examples: 示例''',
        schema_path="se_kb/diagrams/dfd/concepts/elements.json",
        prompt_path=None,
        examples=["外部实体", "处理过程", "数据流", "数据存储", "命名规范", "层次结构", "顶层图", "0层图"],
        min_confidence=0.65,
    ),
    
    # diagrams/dfd/examples/
    KnowledgeType(
        type_id="diagrams.dfd.examples",
        name="DFD 示例案例",
        brief="完整的 DFD 实际案例：包含业务场景、需求描述、DFD 四要素抽取结果",
        description='''对应目录: se_kb/diagrams/dfd/examples/
包含文件: library_management.json, atm_balance_inquiry.json, ecommerce_checkout.json 等
内容结构:
- case_name: 案例名称
- description: 业务描述
- requirements_text: 需求文本列表
- dfd_elements:
  - external_entities: [{id, name}]
  - processes: [{id, name}]
  - data_stores: [{id, name}]
  - data_flows: [{from, to, data}]''',
        schema_path="se_kb/diagrams/dfd/examples/library_management.json",
        prompt_path=None,
        examples=["ATM", "图书馆", "订单系统", "支付", "电商", "医院系统", "选课系统", "案例"],
        min_confidence=0.7,
    ),
    
    # diagrams/dfd/rules/
    KnowledgeType(
        type_id="diagrams.dfd.rules",
        name="DFD 建模规则",
        brief="数据流图建模的规则和约束：数据平衡、父子平衡、命名规则、分解规则等",
        description='''对应目录: se_kb/diagrams/dfd/rules/
包含文件: dfd_modeling_rules.json, dfd_theory_rules.json
内容结构:
- id: 规则标识 (r_001_xxx)
- name: 规则名称
- detail: 规则详细描述
- level: error | warning | info
- source: 来源
- check: manual | auto''',
        schema_path="se_kb/diagrams/dfd/rules/dfd_modeling_rules.json",
        prompt_path=None,
        examples=["规则", "约束", "必须", "不得", "平衡", "分解", "命名规则", "校验"],
        min_confidence=0.65,
    ),
    
    # diagrams/dfd/templates/
    KnowledgeType(
        type_id="diagrams.dfd.templates",
        name="DFD 模板库",
        brief="可重用的 DFD 结构模板：顶层模板、分解模板、数据存储交互模板、异常处理模板",
        description='''对应目录: se_kb/diagrams/dfd/templates/
包含文件: dfd_templates.json
内容结构:
- categories: 模板分类
  - id: 分类标识
  - name: 分类名称
  - templates: 模板列表
    - id, name, dfd_level, pattern_type
    - placeholders: 占位符
    - structure: 结构定义 (nodes, data_flows)
    - applicable_scenarios: 适用场景
    - notes: 说明''',
        schema_path="se_kb/diagrams/dfd/templates/dfd_templates.json",
        prompt_path=None,
        examples=["模板", "三段式", "CRUD", "工作流", "顶层图模板", "分解模板", "交互模板"],
        min_confidence=0.65,
    ),
    
    # diagrams/dfd/validation/
    KnowledgeType(
        type_id="diagrams.dfd.validation",
        name="DFD 校验规则",
        brief="用于验证 DFD 正确性的校验规则：结构校验、命名校验、一致性校验",
        description='''对应目录: se_kb/diagrams/dfd/validation/
包含文件: dfd_balance_checks.json
内容结构:
- validation_rules: 校验规则列表
  - id: 规则标识 (v_001_xxx)
  - name: 规则名称
  - definition: 规则定义
  - detect_logic: 检测逻辑
  - severity: error | warning | info
  - pattern_hint: 正则模式
  - error_message: 错误提示''',
        schema_path="se_kb/diagrams/dfd/validation/dfd_balance_checks.json",
        prompt_path=None,
        examples=["校验", "检查", "验证", "错误", "警告", "平衡检查", "命名检查"],
        min_confidence=0.6,
    ),
    
    # diagrams/dfd/levels/
    KnowledgeType(
        type_id="diagrams.dfd.levels",
        name="DFD 层次分解",
        brief="DFD 的层次分解原则：父子平衡、深度控制、粒度均匀、分解规则",
        description='''对应目录: se_kb/diagrams/dfd/levels/
包含文件: levels.json
内容结构:
- leveling_principles: 分层原则
  - id, description, detection_hint
- decomposition_rules: 分解规则
  - id, description, threshold''',
        schema_path="se_kb/diagrams/dfd/levels/levels.json",
        prompt_path=None,
        examples=["层次", "分解", "分层", "深度", "粒度", "子图", "父图", "平衡"],
        min_confidence=0.6,
    ),
    
    # ========================================================
    # theory/ - 软件工程理论知识
    # ========================================================
    KnowledgeType(
        type_id="theory",
        name="软件工程理论",
        brief="软件工程核心理论概念：系统工程、需求分析、结构化分析、数据流图理论、结构图理论",
        description='''对应目录: se_kb/theory/
包含文件: structured_analysis.json, structure_rules.json
内容结构:
- concepts: 概念列表
  - id, name, english_term, definition
  - representation: 表示类型
  - source, source_location, confidence
- principles: 原则列表
  - id, detail''',
        schema_path="se_kb/theory/structured_analysis.json",
        prompt_path=None,
        examples=["系统工程", "需求分析", "结构化分析", "结构图", "模块", "耦合", "内聚"],
        min_confidence=0.65,
    ),
    
    # ========================================================
    # mappings/ - 映射与抽取配置
    # ========================================================
    KnowledgeType(
        type_id="mappings",
        name="语义映射与抽取配置",
        brief="用于知识抽取的语义映射：语义线索、语言模式、抽取指南",
        description='''对应目录: se_kb/mappings/
包含文件: semantic_cues.json, linguistic_patterns.json, extraction_guidelines.json
内容结构:
- semantic_cues: 语义线索词（按元素类型分组）
- linguistic_patterns: 语言模式（条件、迭代、数据交换等）
- extraction_guidelines: 抽取策略和规则''',
        schema_path="se_kb/mappings/semantic_cues.json",
        prompt_path=None,
        examples=["语义", "映射", "模式", "线索", "抽取", "识别", "信号"],
        min_confidence=0.6,
    ),
    
    # ========================================================
    # schema/ - Schema 定义
    # ========================================================
    KnowledgeType(
        type_id="schema",
        name="Schema 定义",
        brief="知识结构的 JSON Schema 定义：字段规范、ID 模式、必需属性、验证规则",
        description='''对应目录: se_kb/schema/
包含文件: dfd_schema.json
内容结构: 标准 JSON Schema 格式
- $schema, title, type
- required: 必需字段
- properties: 字段定义
- definitions: 类型定义
- pattern: ID 正则模式''',
        schema_path="se_kb/schema/dfd_schema.json",
        prompt_path=None,
        examples=["Schema", "结构", "字段", "属性", "模式", "验证", "规范"],
        min_confidence=0.6,
    ),
    
    # ========================================================
    # domain/ - 领域知识（预留）
    # ========================================================
    KnowledgeType(
        type_id="domain",
        name="领域知识",
        brief="特定业务领域的专业知识：行业术语、业务规则、领域模型",
        description='''对应目录: se_kb/domain/
预留目录，用于存放特定领域知识
内容结构（规划中）:
- domain_id: 领域标识
- name: 领域名称
- terms: 术语表
- rules: 业务规则
- models: 领域模型''',
        schema_path=None,
        prompt_path=None,
        examples=["领域", "行业", "业务", "术语", "专业"],
        min_confidence=0.6,
        enabled=True,  # 启用但内容较少
    ),
    
    # ========================================================
    # examples/ - 通用示例（预留）
    # ========================================================
    KnowledgeType(
        type_id="examples",
        name="通用示例",
        brief="通用的知识抽取示例和参考案例",
        description='''对应目录: se_kb/examples/
预留目录，用于存放通用示例
内容结构（规划中）:
- example_id: 示例标识
- title: 标题
- input: 输入内容
- output: 期望输出
- annotations: 标注说明''',
        schema_path=None,
        prompt_path=None,
        examples=["示例", "案例", "参考", "样例"],
        min_confidence=0.6,
        enabled=True,
    ),
    
    # ========================================================
    # rules/ - 通用规则（预留）
    # ========================================================
    KnowledgeType(
        type_id="rules",
        name="通用规则",
        brief="通用的业务规则和约束条件",
        description='''对应目录: se_kb/rules/
预留目录，用于存放通用规则
内容结构（规划中）:
- rule_id: 规则标识
- type: 规则类型
- condition: 条件
- action: 动作
- priority: 优先级''',
        schema_path=None,
        prompt_path=None,
        examples=["规则", "约束", "条件", "动作"],
        min_confidence=0.6,
        enabled=True,
    ),
]


def get_se_kb_types():
    """获取 SE-KB 知识类型列表"""
    return SE_KB_TYPES


def get_se_kb_type_ids():
    """获取所有类型 ID"""
    return [t.type_id for t in SE_KB_TYPES]


