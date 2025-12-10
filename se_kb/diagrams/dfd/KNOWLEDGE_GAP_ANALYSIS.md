# 📊 DFD 知识库差距分析与补充计划

> 目标：确保 Agent 调用知识库后能画出**完整、高质量、可视化**的数据流图

---

## 一、当前知识库现状

### ✅ 已有内容清单

| 目录 | 文件 | 内容概述 | 完整度 |
|------|------|----------|--------|
| **concepts/** | 13 个文件 | | |
| | `elements.json` | 四大核心元素（外部实体、处理、数据流、数据存储）定义 | ⭐⭐⭐⭐⭐ |
| | `hierarchy.json` | Level-0/1/n 层级结构定义 | ⭐⭐⭐⭐ |
| | `naming_guidelines.json` | 元素命名规范与反例 | ⭐⭐⭐⭐⭐ |
| | `semantics.json` | 语义约束（读写方向、连接规则） | ⭐⭐⭐⭐⭐ |
| | `modelling_principles.json` | 建模五大原则 | ⭐⭐⭐⭐ |
| | `id_conventions.json` | ID 前缀与正则模式 | ⭐⭐⭐⭐⭐ |
| | `data_dictionary.json` | 数据字典结构与示例 | ⭐⭐⭐⭐ |
| | `process_spec_templates.json` | 加工规约模板（结构化语言、判定表、判定树） | ⭐⭐⭐⭐⭐ |
| | `advanced_consistency.json` | 高级一致性约束 | ⭐⭐⭐⭐ |
| | `parallelism_and_aggregation.json` | 并行与聚合模式 | ⭐⭐⭐⭐ |
| | `error_and_timeout_concepts.json` | 异常与超时处理概念 | ⭐⭐⭐ |
| | `events_and_timing.json` | 事件与时序概念 | ⭐⭐⭐ |
| | `data_privacy_compliance.json` | 数据隐私合规 | ⭐⭐⭐ |
| **rules/** | 2 个文件 | | |
| | `dfd_modeling_rules.json` | 9 条建模校验规则 | ⭐⭐⭐⭐ |
| | `dfd_theory_rules.json` | 7 条理论规则 + 参考来源 | ⭐⭐⭐⭐ |
| **validation/** | 1 个文件 | | |
| | `dfd_balance_checks.json` | 9 条校验规则（平衡、命名） | ⭐⭐⭐ |
| **levels/** | 1 个文件 | | |
| | `levels.json` | 分层原则与分解规则 | ⭐⭐⭐ |
| **templates/** | 1 个文件 | | |
| | `dfd_templates.json` | 6 类 DFD 结构模板 | ⭐⭐⭐⭐⭐ |
| **examples/** | 15 个文件 | ATM、电商、图书馆、医院、支付、IoT 等 | ⭐⭐⭐⭐⭐ |
| **schema/** | 1 个文件 | | |
| | `dfd_schema.json` | JSON Schema 完整校验 | ⭐⭐⭐⭐⭐ |

### 📈 整体评估

- **理论概念**：完整度 90%
- **建模规则**：完整度 85%
- **示例案例**：完整度 95%
- **操作指南**：完整度 30% ❌
- **可视化输出**：完整度 10% ❌
- **质量控制**：完整度 40% ❌

---

## 二、需要补充的知识清单

### 📌 P0 级（必须补充）

---

#### 1. 绘图步骤指南
**文件**: `concepts/drawing_steps.json`

**搜索关键词**:
```
数据流图 绘制步骤 方法
DFD 画法 教程 步骤
如何画数据流图 从需求到DFD
数据流图 建模过程 步骤
```

**期望内容结构**:
```json
{
  "description": "从需求到 DFD 的系统化绘图步骤指南",
  "steps": [
    {
      "step": 1,
      "name": "确定系统边界",
      "description": "明确系统范围，识别系统与外界的交互边界",
      "inputs": ["需求文档", "用户访谈"],
      "outputs": ["系统边界说明"],
      "tips": ["关注'系统应该做什么'而非'怎么做'"],
      "common_mistakes": ["边界过大或过小"]
    },
    {
      "step": 2,
      "name": "识别外部实体",
      "description": "找出与系统交互的所有外部角色、系统或组织",
      "signal_words": ["用户", "客户", "管理员", "第三方系统", "外部服务"],
      "questions_to_ask": [
        "谁向系统提供数据？",
        "谁从系统获取数据？",
        "系统与哪些外部系统交互？"
      ]
    },
    {
      "step": 3,
      "name": "确定主要数据流",
      "description": "识别系统的输入和输出数据",
      "signal_words": ["发送", "接收", "提交", "返回", "获取", "传递"],
      "tips": ["先画进出系统边界的数据流"]
    },
    {
      "step": 4,
      "name": "识别处理过程",
      "description": "确定对数据进行变换的核心功能",
      "signal_words": ["验证", "计算", "处理", "生成", "查询", "更新", "检查"],
      "naming_rule": "动词 + 名词"
    },
    {
      "step": 5,
      "name": "确定数据存储",
      "description": "识别系统需要持久保存的数据",
      "signal_words": ["数据库", "文件", "记录", "存储", "表", "库"],
      "tips": ["只有处理过程可以访问数据存储"]
    },
    {
      "step": 6,
      "name": "绘制顶层图 (Level-0)",
      "description": "画出系统与外部实体的整体交互",
      "rules": [
        "只有一个处理（代表整个系统）",
        "不出现数据存储",
        "展示所有外部实体和主要数据流"
      ]
    },
    {
      "step": 7,
      "name": "分解细化 (Level-1+)",
      "description": "逐层分解处理过程",
      "rules": [
        "每层 3-7 个子处理",
        "保持父子图平衡",
        "直到基本加工为止"
      ]
    },
    {
      "step": 8,
      "name": "验证与检查",
      "description": "检查 DFD 的完整性和正确性",
      "checklist": [
        "所有处理都有输入和输出？",
        "父子图数据流平衡？",
        "无直连的外部实体/数据存储？",
        "命名规范统一？"
      ]
    }
  ]
}
```

---

#### 2. 需求-DFD 映射规则
**文件**: `mappings/requirements_to_dfd.json`

**搜索关键词**:
```
需求分析 数据流图 映射
从需求文档提取DFD元素
自然语言 DFD 转换
需求描述 识别 外部实体 处理 数据流
```

**期望内容结构**:
```json
{
  "description": "从自然语言需求识别 DFD 元素的映射规则",
  "entity_identification": {
    "external_entity": {
      "signal_words": ["用户", "客户", "管理员", "操作员", "供应商", "银行", "第三方", "外部系统", "服务提供商"],
      "sentence_patterns": [
        "{角色}可以...",
        "{角色}需要...",
        "系统向{角色}发送...",
        "从{角色}接收..."
      ],
      "examples": [
        {"text": "用户可以查询账户余额", "entity": "用户"},
        {"text": "系统向银行发送转账请求", "entity": "银行"}
      ]
    },
    "process": {
      "signal_verbs": ["验证", "计算", "处理", "生成", "查询", "更新", "检查", "审核", "创建", "删除", "修改", "发送", "接收", "分析", "汇总"],
      "sentence_patterns": [
        "系统{动词}{名词}",
        "需要{动词}{名词}",
        "执行{名词}操作"
      ],
      "naming_transform": "动词 + 名词 → 处理名称",
      "examples": [
        {"text": "系统验证用户密码", "process": "验证密码"},
        {"text": "计算订单总金额", "process": "计算订单金额"}
      ]
    },
    "data_store": {
      "signal_words": ["数据库", "文件", "记录", "存储", "表", "库", "档案", "日志", "缓存"],
      "sentence_patterns": [
        "保存到{存储}",
        "从{存储}读取",
        "存入{存储}",
        "记录在{存储}中"
      ],
      "examples": [
        {"text": "将订单信息保存到订单数据库", "store": "订单数据库"},
        {"text": "从用户表中查询用户信息", "store": "用户表"}
      ]
    },
    "data_flow": {
      "signal_words": ["发送", "传递", "返回", "提交", "获取", "请求", "响应", "通知", "报告"],
      "identification_rules": [
        "动词的宾语通常是数据流名称",
        "介词短语中的数据描述",
        "输入输出的数据名称"
      ],
      "examples": [
        {"text": "用户提交登录请求", "flow": "登录请求"},
        {"text": "系统返回查询结果", "flow": "查询结果"}
      ]
    }
  },
  "relationship_patterns": {
    "input_pattern": {
      "description": "外部实体向系统输入数据",
      "patterns": ["{实体}提交/发送/输入{数据}"],
      "dfd_structure": "外部实体 --数据流--> 处理"
    },
    "output_pattern": {
      "description": "系统向外部实体输出数据",
      "patterns": ["系统向{实体}发送/返回/显示{数据}"],
      "dfd_structure": "处理 --数据流--> 外部实体"
    },
    "store_write": {
      "description": "处理写入数据存储",
      "patterns": ["将{数据}保存/存入/记录到{存储}"],
      "dfd_structure": "处理 --数据流--> 数据存储"
    },
    "store_read": {
      "description": "处理读取数据存储",
      "patterns": ["从{存储}读取/查询/获取{数据}"],
      "dfd_structure": "数据存储 --数据流--> 处理"
    }
  }
}
```

---

#### 3. 可视化输出规范
**文件**: `mappings/visualization_formats.json`

**搜索关键词**:
```
数据流图 可视化工具 格式
DFD Mermaid PlantUML 语法
数据流图 绘图软件 导出格式
DFD 图形表示 SVG
```

**期望内容结构**:
```json
{
  "description": "DFD JSON 到可视化格式的转换规范",
  "formats": {
    "mermaid": {
      "description": "Mermaid flowchart 语法",
      "template": "```mermaid\nflowchart LR\n  %% External Entities\n  {entities}\n  %% Processes\n  {processes}\n  %% Data Stores\n  {stores}\n  %% Data Flows\n  {flows}\n```",
      "element_syntax": {
        "external_entity": "E1[/用户\\]",
        "process": "P1((验证密码))",
        "data_store": "DS1[(账户数据库)]",
        "data_flow": "E1 -->|登录请求| P1"
      },
      "example": "flowchart LR\n  E1[/用户\\]\n  P1((验证密码))\n  DS1[(账户库)]\n  E1 -->|用户名密码| P1\n  P1 -->|查询| DS1\n  DS1 -->|账户信息| P1\n  P1 -->|登录结果| E1"
    },
    "plantuml": {
      "description": "PlantUML 语法",
      "template": "@startuml\n!define ENTITY(e) rectangle e\n!define PROCESS(p) usecase p\n!define STORE(s) database s\n{elements}\n{flows}\n@enduml",
      "example": "@startuml\nactor 用户 as E1\nusecase \"验证密码\" as P1\ndatabase \"账户库\" as DS1\nE1 --> P1 : 用户名密码\nP1 --> DS1 : 查询\nDS1 --> P1 : 账户信息\nP1 --> E1 : 登录结果\n@enduml"
    },
    "graphviz_dot": {
      "description": "Graphviz DOT 语法",
      "template": "digraph DFD {\n  rankdir=LR;\n  {node_definitions}\n  {edge_definitions}\n}",
      "node_styles": {
        "external_entity": "shape=box, style=filled, fillcolor=lightgray",
        "process": "shape=ellipse, style=filled, fillcolor=lightyellow",
        "data_store": "shape=cylinder, style=filled, fillcolor=lightblue"
      }
    },
    "drawio_xml": {
      "description": "Draw.io XML 格式（复杂，建议使用模板）",
      "note": "推荐使用 Mermaid 或 PlantUML 简化输出"
    }
  },
  "conversion_rules": {
    "id_mapping": "使用 DFD JSON 中的 id 作为节点标识",
    "name_display": "使用 name 作为显示文本",
    "flow_label": "使用 data_flow.name 作为边的标签",
    "direction": "默认 LR（左到右），可配置 TB（上到下）"
  }
}
```

---

### 📌 P1 级（重要补充）

---

#### 4. 常见错误库
**文件**: `validation/common_errors.json`

**搜索关键词**:
```
数据流图 常见错误 问题
DFD 建模错误 黑洞 奇迹
数据流图 错误类型 修正
```

**期望内容结构**:
```json
{
  "description": "DFD 建模常见错误类型、识别方法与修复建议",
  "errors": [
    {
      "id": "err_black_hole",
      "name": "黑洞（Black Hole）",
      "definition": "处理有输入但无输出，数据进入后消失",
      "detection": "检查 process.outputs 是否为空",
      "example": {
        "wrong": "P1: 接收订单（只有输入，无输出）",
        "correct": "P1: 接收订单 → 输出: 订单确认"
      },
      "fix": "添加输出数据流或检查是否遗漏后续处理"
    },
    {
      "id": "err_miracle",
      "name": "奇迹（Miracle）",
      "definition": "处理有输出但无输入，凭空产生数据",
      "detection": "检查 process.inputs 是否为空",
      "fix": "添加输入数据流或外部实体"
    },
    {
      "id": "err_gray_hole",
      "name": "灰洞（Gray Hole）",
      "definition": "处理的部分输入未被使用于任何输出",
      "detection": "分析输入数据流是否都参与了输出生成",
      "fix": "移除无用输入或补充使用该输入的输出"
    },
    {
      "id": "err_direct_connection",
      "name": "直连违规",
      "definition": "外部实体之间、数据存储之间、或外部实体与数据存储直接连接",
      "detection": "检查数据流的 source/target 是否绕过处理",
      "fix": "在中间插入处理过程"
    },
    {
      "id": "err_orphan_element",
      "name": "孤儿元素",
      "definition": "元素没有任何数据流连接",
      "detection": "检查元素的入度和出度是否都为 0",
      "fix": "添加数据流或移除无关元素"
    },
    {
      "id": "err_unbalanced",
      "name": "父子不平衡",
      "definition": "子图的边界数据流与父图处理的输入输出不一致",
      "detection": "比较父层 I/O 与子图边界流集合",
      "fix": "调整子图边界流或父图数据流使其一致"
    },
    {
      "id": "err_poor_naming",
      "name": "命名不当",
      "definition": "使用空泛词汇如'处理'、'数据'、'信息'",
      "detection": "匹配命名规范正则，检查是否在禁用词列表",
      "fix": "使用具体的业务术语重命名"
    },
    {
      "id": "err_granularity_mismatch",
      "name": "粒度不均",
      "definition": "同一层级的处理复杂度差异过大",
      "detection": "比较同层处理的子图深度或描述复杂度",
      "fix": "合并简单处理或拆分复杂处理"
    }
  ]
}
```

---

#### 5. 质量检查清单
**文件**: `validation/quality_checklist.json`

**搜索关键词**:
```
数据流图 检查清单 验证
DFD 质量标准 评审
数据流图 评审要点 检查项
```

**期望内容结构**:
```json
{
  "description": "DFD 质量检查清单，用于自动或人工评审",
  "checklist": {
    "completeness": {
      "name": "完整性检查",
      "items": [
        {"id": "c1", "check": "所有外部实体都有数据交换", "severity": "error"},
        {"id": "c2", "check": "所有处理都有输入和输出", "severity": "error"},
        {"id": "c3", "check": "所有数据存储都被读或写", "severity": "warning"},
        {"id": "c4", "check": "顶层图包含所有外部实体", "severity": "error"},
        {"id": "c5", "check": "基本加工有加工规约", "severity": "warning"}
      ]
    },
    "consistency": {
      "name": "一致性检查",
      "items": [
        {"id": "s1", "check": "父子图数据流平衡", "severity": "error"},
        {"id": "s2", "check": "命名语言统一（中/英）", "severity": "warning"},
        {"id": "s3", "check": "ID 格式符合规范", "severity": "error"},
        {"id": "s4", "check": "数据流名称与数据字典一致", "severity": "warning"}
      ]
    },
    "correctness": {
      "name": "正确性检查",
      "items": [
        {"id": "r1", "check": "无黑洞（处理无输出）", "severity": "error"},
        {"id": "r2", "check": "无奇迹（处理无输入）", "severity": "error"},
        {"id": "r3", "check": "无直连（外部实体/存储直接相连）", "severity": "error"},
        {"id": "r4", "check": "数据流方向正确（读/写）", "severity": "error"},
        {"id": "r5", "check": "无悬空数据流", "severity": "error"}
      ]
    },
    "readability": {
      "name": "可读性检查",
      "items": [
        {"id": "d1", "check": "每层处理数量 3-7 个", "severity": "warning"},
        {"id": "d2", "check": "数据流交叉最小化", "severity": "info"},
        {"id": "d3", "check": "处理命名为'动词+名词'", "severity": "warning"},
        {"id": "d4", "check": "避免空泛命名", "severity": "warning"}
      ]
    }
  },
  "scoring": {
    "error_weight": -10,
    "warning_weight": -3,
    "info_weight": -1,
    "pass_threshold": 70
  }
}
```

---

#### 6. 符号标准规范
**文件**: `concepts/notation_standards.json`

**搜索关键词**:
```
数据流图 符号 Gane-Sarson Yourdon
DFD 符号规范 标准
数据流图 图形符号 表示法
```

**期望内容结构**:
```json
{
  "description": "DFD 两大主流符号体系对比与选择建议",
  "standards": {
    "yourdon_demarco": {
      "name": "Yourdon-DeMarco 符号",
      "origin": "1970s, Edward Yourdon & Tom DeMarco",
      "symbols": {
        "external_entity": {"shape": "矩形/方框", "description": "表示外部实体"},
        "process": {"shape": "圆形/椭圆", "description": "表示处理过程"},
        "data_store": {"shape": "两条平行线（开口矩形）", "description": "表示数据存储"},
        "data_flow": {"shape": "带箭头的线", "description": "表示数据流动方向"}
      },
      "usage": "学术界、教科书常用"
    },
    "gane_sarson": {
      "name": "Gane-Sarson 符号",
      "origin": "1979, Chris Gane & Trish Sarson",
      "symbols": {
        "external_entity": {"shape": "方框", "description": "表示外部实体"},
        "process": {"shape": "圆角矩形（分三栏：ID/名称/位置）", "description": "表示处理过程"},
        "data_store": {"shape": "右侧开口的矩形", "description": "表示数据存储"},
        "data_flow": {"shape": "带箭头的线", "description": "表示数据流动方向"}
      },
      "usage": "工业界、商业工具常用"
    }
  },
  "recommendation": {
    "default": "Yourdon-DeMarco",
    "reason": "更简洁，适合快速建模和教学",
    "tool_mapping": {
      "mermaid": "类似 Yourdon 风格（圆形处理）",
      "visio": "支持两种符号",
      "draw.io": "支持两种符号"
    }
  }
}
```

---

### 📌 P2 级（建议补充）

---

#### 7. 层级分解决策树
**文件**: `levels/decomposition_decision.json`

**搜索关键词**:
```
数据流图 分解 何时停止
DFD 基本加工 判断
处理分解 粒度 决策
```

**期望内容结构**:
```json
{
  "description": "判断处理是否需要继续分解的决策规则",
  "decision_tree": {
    "question_1": {
      "question": "该处理能否用一段结构化语言（50行内）完整描述？",
      "yes": "停止分解，编写加工规约",
      "no": "继续分解"
    },
    "question_2": {
      "question": "该处理是否涉及多个独立的子功能？",
      "yes": "继续分解，每个子功能成为子处理",
      "no": "考虑停止"
    },
    "question_3": {
      "question": "分解后子处理数量是否超过 7 个？",
      "yes": "重新划分边界，考虑分组",
      "no": "分解合理"
    },
    "question_4": {
      "question": "多个处理中是否存在重复逻辑？",
      "yes": "提取为公共子处理",
      "no": "保持现状"
    }
  },
  "primitive_process_criteria": [
    "可以用结构化语言完整描述",
    "不涉及多个独立子功能",
    "输入输出关系清晰明确",
    "业务逻辑相对简单"
  ]
}
```

---

#### 8. 布局与可视化规范
**文件**: `concepts/layout_guidelines.json`

**搜索关键词**:
```
数据流图 布局 排版
DFD 图形布局 设计
数据流图 绘图 美观
```

**期望内容结构**:
```json
{
  "description": "DFD 布局与可视化美观性指南",
  "layout_principles": {
    "flow_direction": {
      "primary": "从左到右（LR）",
      "alternative": "从上到下（TB）",
      "guideline": "主数据流应遵循统一方向"
    },
    "element_placement": {
      "external_entities": "放置在图的左右两侧（输入左、输出右）",
      "data_stores": "放置在图的下方或处理之间",
      "processes": "居中布局，按数据流顺序排列"
    },
    "spacing": {
      "horizontal": "元素间距 60-80px",
      "vertical": "层级间距 40-60px"
    },
    "crossing_minimization": {
      "rule": "尽量减少数据流交叉",
      "technique": "调整元素位置或使用弯曲连线"
    }
  },
  "visual_style": {
    "colors": {
      "external_entity": "#E8E8E8 (浅灰)",
      "process": "#FFFACD (浅黄)",
      "data_store": "#ADD8E6 (浅蓝)",
      "data_flow": "#333333 (深灰线条)"
    },
    "fonts": {
      "element_name": "12-14px, 无衬线",
      "flow_label": "10-12px"
    }
  }
}
```

---

### 📌 P3 级（可选补充）

---

#### 9. 迭代优化指南
**文件**: `rules/optimization_guide.json`

**搜索关键词**:
```
数据流图 优化 重构
DFD 改进 迭代
数据流图 质量提升
```

---

#### 10. 测试用例库
**文件**: `validation/test_cases.json`

**搜索关键词**:
```
数据流图 测试用例 验证
DFD 建模 案例测试
需求 DFD 期望输出
```

---

## 三、补充方法

### 方法 1：使用搜索引擎爬取

```powershell
# 使用 DuckDuckGo 搜索（免费）
python scripts/run_web_crawl.py --serp --query "数据流图 绘制步骤 方法 教程" --engine duckduckgo --limit 10

# 使用 SerpAPI 搜索（需要 API Key）
python scripts/run_web_crawl.py --serp --query "DFD 建模 常见错误 黑洞 奇迹" --engine google --limit 10
```

### 方法 2：指定 URL 爬取

```powershell
# 爬取已知的高质量资源
python scripts/test_crawl_single.py "https://www.visual-paradigm.com/guide/data-flow-diagram/"
python scripts/test_crawl_single.py "https://www.ibm.com/cn-zh/topics/data-flow-diagram"
python scripts/test_crawl_single.py "https://www.geeksforgeeks.org/developing-dfd-model-of-system/"
```

### 方法 3：运行知识抽取

```powershell
# 强制抽取特定类型
python exporter_v2.py --input-glob "data/parsed/*.json" --force-types diagrams.dfd.concepts,diagrams.dfd.rules
```

### 方法 4：手动创建/编辑

直接在 `se_kb/diagrams/dfd/` 对应目录下创建 JSON 文件。

---

## 四、验证清单

补充完成后，使用以下方法验证：

```powershell
# 1. 检查类型注册
python scripts/test_pipeline.py --registry

# 2. 测试抽取效果
python scripts/test_pipeline.py "data/parsed/xxx.json" --force-types diagrams.dfd.concepts

# 3. 查看抽取结果
Get-Content test_output\pipeline_diagrams.dfd.concepts.json | ConvertFrom-Json
```

---

## 五、完成标准

| 指标 | 当前 | 目标 |
|------|------|------|
| 操作指南完整度 | 30% | 90% |
| 可视化输出能力 | 10% | 80% |
| 质量控制覆盖 | 40% | 85% |
| Agent 可独立画图 | ❌ | ✅ |

---

## 六、推荐的爬取 URL 列表

### 绘图步骤相关
- https://www.visual-paradigm.com/guide/data-flow-diagram/
- https://www.lucidchart.com/pages/data-flow-diagram
- https://creately.com/guides/data-flow-diagram-tutorial/
- https://www.edrawsoft.com/how-to-create-dfd.html

### 规则与错误相关
- https://www.geeksforgeeks.org/developing-dfd-model-of-system/
- https://www.ibm.com/cn-zh/topics/data-flow-diagram
- https://en.wikipedia.org/wiki/Data-flow_diagram
- https://www.tutorialspoint.com/software_engineering/data_flow_diagram.htm

### 符号标准相关
- https://www.visual-paradigm.com/guide/data-flow-diagram/dfd-notations/
- https://www.smartdraw.com/data-flow-diagram/

### 中文资源
- https://blog.csdn.net/search?q=数据流图绘制步骤
- https://www.zhihu.com/search?q=数据流图画法
- https://cloud.tencent.com/developer/search?q=DFD建模

---

*文档生成时间: 2024-12-09*
*版本: 1.0*


