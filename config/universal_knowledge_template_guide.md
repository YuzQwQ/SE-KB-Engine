# 通用知识库模板配置文档

## 概述

`universal_knowledge_template.json` 是一个通用知识库的JSON结构模板配置文件，用于定义支持需求转换的生成和验证的知识库结构。该模板为爬取的内容提供标准化的知识库格式，支持从需求文档到设计图（如DFD、UML等）的转换。

## 文件信息

- **文件路径**: `config/universal_knowledge_template.json`
- **版本**: 1.0.0
- **用途**: 为爬取内容提供标准化知识库格式
- **支持转换**: 需求文档 → 设计图（DFD、UML、架构图等）

## 主要结构

### 1. 基本信息

```json
{
  "universal_knowledge_base": {
    "name": "通用知识库格式",
    "description": "支持需求转换的生成和验证的通用知识库结构",
    "version": "1.0.0"
  }
}
```

### 2. JSON数据结构定义 (json_structure)

#### 2.1 元数据部分 (metadata)

记录知识条目的基本信息和来源：

| 字段 | 类型 | 说明 |
|------|------|------|
| `knowledge_id` | string | 知识条目的唯一标识符 |
| `title` | string | 知识条目的标题 |
| `description` | string | 知识条目的描述 |
| `version` | string | 知识条目的版本号 |
| `created_time` | datetime | 创建时间 (ISO 8601格式) |
| `updated_time` | datetime | 最后更新时间 (ISO 8601格式) |

**来源信息 (source_info)**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_url` | string | 原始来源URL |
| `source_type` | string | 来源类型（官方文档、博客、论文等） |
| `crawl_time` | datetime | 爬取时间 |
| `extraction_method` | string | 提取方法（自动爬取、手工整理等） |
| `reliability_score` | float | 可靠性评分 (0.0-1.0) |

#### 2.2 需求和转换类型定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `requirement_type` | string | 需求类型（功能需求、非功能需求、业务需求等） |
| `target_conversion_type` | string | 目标转换类型（DFD、UML、架构图等） |

#### 2.3 生成知识部分 (generation_knowledge)

用于指导如何生成目标输出的知识：

##### 2.3.1 概念定义 (concepts)

| 字段 | 类型 | 说明 |
|------|------|------|
| `concept_id` | string | 概念的唯一标识符 |
| `name` | string | 概念名称 |
| `definition` | string | 概念的详细定义 |
| `category` | string | 概念所属的分类 |
| `attributes` | object | 概念的属性集合（键值对） |
| `relationships` | array | 与其他概念的关系（数组形式） |

##### 2.3.2 生成规则 (rules)

| 字段 | 类型 | 说明 |
|------|------|------|
| `rule_id` | string | 规则的唯一标识符 |
| `type` | string | 规则类型（语法规则、语义规则、格式规则等） |
| `condition` | string | 规则的触发条件 |
| `action` | string | 满足条件时执行的动作 |
| `priority` | integer | 规则优先级（数字越大优先级越高） |
| `applicable_scenarios` | array | 适用场景列表 |

##### 2.3.3 模式和模板 (patterns)

| 字段 | 类型 | 说明 |
|------|------|------|
| `pattern_id` | string | 模式的唯一标识符 |
| `name` | string | 模式名称 |
| `template` | string | 模板内容（可包含变量占位符） |
| `variables` | object | 模板变量定义（变量名和类型） |
| `usage_context` | string | 使用上下文和场景 |
| `complexity_level` | string | 复杂度级别（简单、中等、复杂） |

##### 2.3.4 转换方法 (transformations)

| 字段 | 类型 | 说明 |
|------|------|------|
| `transformation_id` | string | 转换方法的唯一标识符 |
| `from_format` | string | 源格式（文本需求、用例图等） |
| `to_format` | string | 目标格式（DFD、时序图等） |
| `steps` | array | 转换步骤的详细描述（有序数组） |
| `tools_required` | array | 所需工具列表 |
| `preconditions` | array | 转换的前置条件 |

#### 2.4 验证知识部分 (validation_knowledge)

用于验证生成结果的质量和正确性：

##### 2.4.1 验证标准 (criteria)

| 字段 | 类型 | 说明 |
|------|------|------|
| `criteria_id` | string | 标准的唯一标识符 |
| `name` | string | 标准名称 |
| `description` | string | 标准的详细描述 |
| `measurement_method` | string | 测量方法 |
| `threshold_values` | object | 阈值设定（最小值、最大值、目标值） |
| `weight` | float | 在整体评估中的权重 (0.0-1.0) |

##### 2.4.2 检查清单 (checklist)

| 字段 | 类型 | 说明 |
|------|------|------|
| `check_id` | string | 检查项的唯一标识符 |
| `category` | string | 检查类别（语法检查、语义检查、格式检查） |
| `description` | string | 检查项的详细描述 |
| `validation_method` | string | 验证方法（自动检查、人工审核） |
| `expected_result` | string | 期望的检查结果 |
| `severity_level` | string | 严重程度（低、中、高、致命） |

##### 2.4.3 错误模式 (error_patterns)

| 字段 | 类型 | 说明 |
|------|------|------|
| `error_id` | string | 错误模式的唯一标识符 |
| `pattern_description` | string | 错误模式的描述 |
| `symptoms` | array | 错误症状列表 |
| `root_causes` | array | 根本原因分析 |
| `solutions` | array | 解决方案列表 |
| `prevention_measures` | array | 预防措施 |

#### 2.5 示例部分 (examples)

提供输入输出和转换过程的具体示例：

##### 2.5.1 输入示例 (input_examples)

| 字段 | 类型 | 说明 |
|------|------|------|
| `example_id` | string | 示例的唯一标识符 |
| `title` | string | 示例标题 |
| `content` | string | 示例内容 |
| `format` | string | 输入格式（自然语言、结构化文本等） |
| `complexity_level` | string | 复杂度级别 |
| `tags` | array | 标签列表（用于分类和搜索） |

##### 2.5.2 输出示例 (output_examples)

| 字段 | 类型 | 说明 |
|------|------|------|
| `example_id` | string | 输出示例的唯一标识符 |
| `input_reference` | string | 对应的输入示例ID |
| `content` | string | 输出内容 |
| `format` | string | 输出格式（JSON、XML、图形描述等） |
| `quality_score` | float | 质量评分 (0.0-1.0) |
| `annotations` | object | 注释信息（解释、备注等） |

##### 2.5.3 转换过程示例 (transformation_examples)

| 字段 | 类型 | 说明 |
|------|------|------|
| `example_id` | string | 转换示例的唯一标识符 |
| `input_example_id` | string | 输入示例引用 |
| `output_example_id` | string | 输出示例引用 |
| `transformation_steps` | array | 详细的转换步骤 |
| `intermediate_results` | array | 中间结果（每个步骤的输出） |
| `notes` | string | 转换过程的说明和注意事项 |

#### 2.6 关系部分 (relationships)

定义知识库之间的关联关系：

| 字段 | 类型 | 说明 |
|------|------|------|
| `related_knowledge_bases` | array | 相关知识库列表 |
| `dependency_graph` | object | 依赖关系图 |
| `cross_references` | array | 交叉引用列表 |

### 3. 提取配置部分 (extraction_config)

用于从原始文本中自动提取知识的配置，定义了各种文本模式和关键词：

#### 3.1 概念提取配置 (concepts)

| 指示词类型 | 关键词列表 | 用途 |
|------------|------------|------|
| `definition_indicators` | ["定义", "概念", "是指", "指的是", "表示"] | 识别概念定义 |
| `category_indicators` | ["类型", "种类", "分类", "类别"] | 识别概念分类 |
| `attribute_indicators` | ["属性", "特征", "特点", "性质"] | 识别概念属性 |

#### 3.2 规则提取配置 (rules)

| 指示词类型 | 关键词列表 | 用途 |
|------------|------------|------|
| `rule_indicators` | ["规则", "约束", "限制", "要求", "必须", "应该"] | 识别规则和约束 |
| `condition_indicators` | ["如果", "当", "在...情况下", "条件"] | 识别条件语句 |
| `action_indicators` | ["则", "那么", "执行", "进行", "操作"] | 识别动作和结果 |

#### 3.3 模式提取配置 (patterns)

| 指示词类型 | 关键词列表 | 用途 |
|------------|------------|------|
| `template_indicators` | ["模板", "模式", "范式", "样式", "格式"] | 识别模板和模式 |
| `usage_indicators` | ["使用", "应用", "适用于", "场景"] | 识别使用场景 |

#### 3.4 转换方法提取配置 (transformations)

| 指示词类型 | 关键词列表 | 用途 |
|------------|------------|------|
| `step_indicators` | ["步骤", "阶段", "过程", "流程"] | 识别步骤和流程 |
| `method_indicators` | ["方法", "技术", "工具", "手段"] | 识别方法和工具 |

#### 3.5 验证相关提取配置 (validation)

| 指示词类型 | 关键词列表 | 用途 |
|------------|------------|------|
| `criteria_indicators` | ["标准", "指标", "准则", "要求"] | 识别验证标准 |
| `error_indicators` | ["错误", "问题", "缺陷", "异常", "故障"] | 识别错误和问题 |

## 使用场景

### 1. 知识库构建
- 为爬取的内容提供统一的结构化格式
- 支持多种来源的知识整合
- 便于知识的检索和管理

### 2. 需求转换
- 支持从自然语言需求到设计图的转换
- 提供转换过程的指导和验证
- 确保转换结果的质量和一致性

### 3. 自动化处理
- 通过提取配置实现自动化知识提取
- 支持批量处理和格式化
- 提高知识库构建效率

## 扩展和定制

### 1. 添加新的知识类型
可以在 `generation_knowledge` 部分添加新的知识类型，如：
- 业务流程知识
- 技术架构知识
- 用户体验知识

### 2. 扩展验证规则
可以在 `validation_knowledge` 部分添加更多验证规则：
- 领域特定的验证标准
- 自定义的检查清单
- 新的错误模式识别

### 3. 增强提取配置
可以在 `extraction_config` 部分添加更多提取模式：
- 特定领域的关键词
- 复杂的文本模式
- 多语言支持

## 最佳实践

### 1. 数据质量
- 确保 `reliability_score` 的准确性
- 定期更新 `source_info` 信息
- 维护版本控制

### 2. 结构一致性
- 遵循统一的命名规范
- 保持字段类型的一致性
- 使用标准化的分类体系

### 3. 可维护性
- 添加详细的描述信息
- 建立清晰的关系映射
- 定期清理过时的数据


## 版本历史

- **v1.0.0** - 初始版本，包含基本的知识库结构定义