# 专注版本配置指南

## 🎯 **专注场景说明**

本系统已优化为**仅支持需求分析和DFD知识提取**，移除了所有其他无关的提示词类型，专注于生成符合知识库格式的需求分析和DFD知识文件。

## 📋 **可用提示词类型**

### 1. requirement_analysis - 需求分析知识提取
- **用途**：从需求分析相关内容中提取结构化知识
- **适用场景**：需求文档、需求规格说明、需求工程文章
- **提取重点**：功能需求、非功能需求、需求分类、需求验证等

### 2. dfd_expert - DFD知识提取  
- **用途**：从数据流图相关内容中提取结构化知识
- **适用场景**：DFD建模、数据流分析、系统流程设计
- **提取重点**：DFD符号、建模规则、分层分解、验证方法等

## ⚙️ **环境变量配置**

```bash
# 系统提示词配置（仅支持以下两个值）
SYSTEM_PROMPT_TYPE=requirement_analysis  # 或 dfd_expert
```

## 🔄 **配置优先级**

1. **优先使用**：`config/system_prompts_focused.json`
2. **回退使用**：`config/system_prompts.json`（旧版本）

## 📝 **使用示例**

```bash
# 提取需求分析知识
SYSTEM_PROMPT_TYPE=requirement_analysis python your_script.py

# 提取DFD知识  
SYSTEM_PROMPT_TYPE=dfd_expert python your_script.py
```

## 🎯 **核心优势**

- ✅ **专注场景**：仅支持需求分析和DFD知识提取
- ✅ **简化配置**：只有两个提示词类型可选
- ✅ **精准提取**：针对知识库格式优化的提示词
- ✅ **减少混淆**：移除了无关的通用分析类型

## 📁 **配置文件**

```
config/
├── system_prompts_focused.json    # 专注版本（优先使用）
├── system_prompts.json           # 旧版本（回退使用）
└── CONFIG_GUIDE_FOCUSED.md       # 本指南
```

---

**注意**：系统已自动配置为优先使用专注版本，无需手动修改代码。