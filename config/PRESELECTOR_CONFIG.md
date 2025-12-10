# LLM Preselector 配置指南

## 概述

LLM Preselector 使用小模型（如 Qwen2.5-7B-Instruct）进行语义级候选片段筛选，替代原有的关键词规则过滤，实现更高的召回率和准确性。

## 环境变量配置

在项目根目录的 `.env` 文件中添加以下配置：

```bash
# ===== Preselector (小模型筛选器) =====
FILTER_BASE_URL=https://api.siliconflow.cn/v1
FILTER_API_KEY=sk-your-api-key-here
FILTER_MODEL_ID=Qwen/Qwen2.5-7B-Instruct

# ===== 主抽取模型 (大模型) =====
KB_BASE_URL=https://api.siliconflow.cn/v1
KB_API_KEY=sk-your-api-key-here
KB_MODEL_ID=Qwen/Qwen2.5-72B-Instruct

# ===== Adapter 模式控制 =====
# 可选值: true, false, auto (默认)
# auto: 如果配置了 FILTER_* 则启用增强模式
USE_ENHANCED_ADAPTERS=auto
```

## 模式说明

### Legacy 模式 (原有)
- 使用基于关键词规则的 adapter
- 不需要 FILTER_* 配置
- DFD 候选只取标题，召回率低
- concepts/rules 基于简单句子切分

### Enhanced 模式 (增强)
- 使用 LLM Preselector 进行语义筛选
- 需要配置 FILTER_* 环境变量
- 完整提取 DFD 相关段落
- 更智能的概念/规则识别

## 切换模式

```bash
# 强制使用增强模式
USE_ENHANCED_ADAPTERS=true

# 强制使用 Legacy 模式
USE_ENHANCED_ADAPTERS=false

# 自动检测（默认，推荐）
USE_ENHANCED_ADAPTERS=auto
```

## 测试

```bash
# 测试 Preselector 是否正常工作
python scripts/test_preselector.py

# 指定测试文件
python scripts/test_preselector.py "data/parsed/your_file.json"
```

## 成本估算

使用 Qwen2.5-7B-Instruct (SiliconFlow):
- 输入: ~¥0.001/1K tokens
- 输出: ~¥0.002/1K tokens
- 单次筛选约 2K-5K input tokens + 1K output tokens
- 估算: 每个网页约 ¥0.005

## 提示词自定义

如需自定义筛选提示词，修改 `adapters/llm_preselector.py` 中的：
- `PRESELECTOR_SYSTEM_PROMPT`: 系统提示词，定义筛选规则
- `PRESELECTOR_USER_PROMPT_TEMPLATE`: 用户提示词模板

## 注意事项

1. 小模型上下文限制：默认截断超过 12000 字符的内容
2. 建议 timeout 设置 60s 以上
3. 如果筛选结果不理想，可尝试调整 system prompt 中的识别特征

