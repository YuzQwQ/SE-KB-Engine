# 📖 知识库构建系统使用指南

## 一、系统概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           完整工作流程                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   搜索关键词  ─→  获取URL  ─→  爬取网页  ─→  知识抽取  ─→  写入知识库         │
│                                                                             │
│   "DFD 绘图"     10个URL    parsed.json   concepts.json   se_kb/...         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、环境配置

### 1. 检查 .env 文件

```bash
# 必需配置
FILTER_BASE_URL=https://api.siliconflow.cn/v1    # 路由模型 API
FILTER_API_KEY=sk-xxx                             # 路由模型 Key
FILTER_MODEL_ID=Qwen/Qwen2.5-7B-Instruct         # 路由模型

KB_BASE_URL=https://api.siliconflow.cn/v1        # 抽取模型 API  
KB_API_KEY=sk-xxx                                 # 抽取模型 Key
KB_MODEL_ID=Qwen/Qwen2.5-72B-Instruct            # 抽取模型

# 可选配置（搜索引擎）
SERPAPI_API_KEY=xxx                               # SerpAPI（Google/Bing）

# 可选配置（图片分析）
VISUAL_MODEL_API_KEY=sk-xxx
VISUAL_MODEL=Pro/Qwen/Qwen2.5-VL-7B-Instruct
```

### 2. 验证环境

```powershell
# 检查配置
python scripts/diagnose_env.py

# 查看已注册的知识类型
python scripts/test_pipeline.py --registry
```

---

## 三、使用流程

### 🔵 流程 A：从搜索引擎开始（推荐）

适用于：不知道具体 URL，需要系统自动搜索

#### 步骤 1：搜索并爬取

```powershell
# 使用 DuckDuckGo（免费，无需 API Key）
python scripts/run_web_crawl.py --serp --query "数据流图 绘制步骤 教程" --engine duckduckgo --limit 10

# 使用 Google（需要 SERPAPI_API_KEY）
python scripts/run_web_crawl.py --serp --query "DFD drawing steps tutorial" --engine google --limit 10
```

#### 步骤 2：查看爬取结果

```powershell
# 列出已爬取的文件
Get-ChildItem data/parsed/*.json | Select-Object Name, LastWriteTime | Sort-Object LastWriteTime -Descending | Select-Object -First 10
```

#### 步骤 3：运行知识抽取

```powershell
# 自动路由（系统判断类型）
python exporter_v2.py --input-glob "data/parsed/*.json"

# 指定抽取类型
python exporter_v2.py --input-glob "data/parsed/*.json" --force-types diagrams.dfd.concepts,diagrams.dfd.rules
```

#### 步骤 4：查看抽取结果

```powershell
# 查看最新的 artifacts
Get-ChildItem se_kb/artifacts -Recurse -Filter "*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 10
```

---

### 🟢 流程 B：从指定 URL 开始

适用于：已知具体的高质量网页 URL

#### 步骤 1：爬取单个网页

```powershell
python scripts/test_crawl_single.py "https://www.visual-paradigm.com/guide/data-flow-diagram/"
```

#### 步骤 2：查看解析结果

```powershell
# 找到刚爬取的文件
Get-ChildItem data/parsed/*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

#### 步骤 3：运行知识抽取

```powershell
# 指定文件抽取
python exporter_v2.py --input-glob "data/parsed/www_visual-paradigm_com*.json" --force-types diagrams.dfd.concepts
```

---

### 🟡 流程 C：批量爬取 URL 列表

适用于：有多个已知 URL 需要处理

#### 步骤 1：创建 URL 文件

```powershell
# 创建 urls.txt 文件
@"
https://www.visual-paradigm.com/guide/data-flow-diagram/
https://www.ibm.com/cn-zh/topics/data-flow-diagram
https://www.geeksforgeeks.org/developing-dfd-model-of-system/
https://www.lucidchart.com/pages/data-flow-diagram
"@ | Out-File -FilePath urls.txt -Encoding UTF8
```

#### 步骤 2：批量爬取

```powershell
python scripts/run_web_crawl.py --url-file urls.txt
```

#### 步骤 3：批量抽取

```powershell
python exporter_v2.py --input-glob "data/parsed/*.json" --force-types diagrams.dfd.concepts,diagrams.dfd.rules
```

---

## 四、知识类型说明

### 当前支持的 12 种类型

| 类型 ID | 名称 | 用途 |
|---------|------|------|
| `diagrams.dfd.concepts` | DFD 概念定义 | 元素定义、命名规范、层次结构 |
| `diagrams.dfd.examples` | DFD 示例案例 | 完整的 DFD 案例 |
| `diagrams.dfd.rules` | DFD 建模规则 | 建模规则和约束 |
| `diagrams.dfd.templates` | DFD 模板库 | 可重用结构模板 |
| `diagrams.dfd.validation` | DFD 校验规则 | 校验和验证规则 |
| `diagrams.dfd.levels` | DFD 层次分解 | 分解原则和规则 |
| `theory` | 软件工程理论 | 系统工程、需求分析理论 |
| `mappings` | 语义映射 | 语义线索、语言模式 |
| `schema` | Schema 定义 | JSON Schema 结构 |
| `domain` | 领域知识 | 特定领域术语 |
| `examples` | 通用示例 | 参考案例 |
| `rules` | 通用规则 | 业务规则 |

### 指定类型抽取

```powershell
# 单类型
python exporter_v2.py --input-glob "data/parsed/*.json" --force-types diagrams.dfd.concepts

# 多类型（逗号分隔）
python exporter_v2.py --input-glob "data/parsed/*.json" --force-types diagrams.dfd.concepts,diagrams.dfd.rules,theory
```

---

## 五、补充知识库实战

### 示例：补充"绘图步骤指南"

根据 `se_kb/diagrams/dfd/KNOWLEDGE_GAP_ANALYSIS.md` 中的指导：

#### 1. 搜索相关内容

```powershell
python scripts/run_web_crawl.py --serp --query "数据流图 绘制步骤 方法 从需求到DFD" --engine duckduckgo --limit 10
```

#### 2. 爬取推荐的高质量 URL

```powershell
python scripts/test_crawl_single.py "https://www.visual-paradigm.com/guide/data-flow-diagram/"
python scripts/test_crawl_single.py "https://creately.com/guides/data-flow-diagram-tutorial/"
```

#### 3. 抽取知识

```powershell
python exporter_v2.py --input-glob "data/parsed/*visual-paradigm*.json" --force-types diagrams.dfd.concepts
python exporter_v2.py --input-glob "data/parsed/*creately*.json" --force-types diagrams.dfd.concepts
```

#### 4. 查看抽取结果

```powershell
# 查看最新的概念抽取结果
Get-ChildItem se_kb/artifacts -Recurse -Filter "diagrams.dfd.concepts.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 3

# 读取内容
Get-Content "se_kb/artifacts/2024/12/09/www.visual-paradigm.com/xxx/diagrams.dfd.concepts.json" | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

#### 5. 整理到正式知识库

如果抽取结果质量好，手动整理到 `se_kb/diagrams/dfd/concepts/drawing_steps.json`

---

## 六、测试与验证

### 测试流水线

```powershell
# 完整流水线测试
python scripts/test_pipeline.py "data/parsed/xxx.json"

# 强制指定类型测试
python scripts/test_pipeline.py "data/parsed/xxx.json" --force-types diagrams.dfd.concepts,theory

# 查看类型注册表
python scripts/test_pipeline.py --registry
```

### 查看测试输出

```powershell
# 测试输出目录
Get-ChildItem test_output/

# 查看抽取结果
Get-Content test_output/pipeline_diagrams.dfd.concepts.json
Get-Content test_output/pipeline_trace.json
```

---

## 七、常用命令速查

### 搜索与爬取

```powershell
# DuckDuckGo 搜索（免费）
python scripts/run_web_crawl.py --serp --query "关键词" --engine duckduckgo --limit 10

# 单个 URL 爬取
python scripts/test_crawl_single.py "https://example.com/page"

# URL 文件批量爬取
python scripts/run_web_crawl.py --url-file urls.txt
```

### 知识抽取

```powershell
# 自动路由抽取
python exporter_v2.py --input-glob "data/parsed/*.json"

# 指定类型抽取
python exporter_v2.py --input-glob "data/parsed/*.json" --force-types 类型1,类型2

# 跳过 Schema 校验
python exporter_v2.py --input-glob "data/parsed/*.json" --skip-validation
```

### 文件查看

```powershell
# 查看已爬取文件
Get-ChildItem data/parsed/*.json | Select Name

# 查看抽取结果
Get-ChildItem se_kb/artifacts -Recurse -Filter "*.json"

# 读取 JSON
Get-Content "文件路径" | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

---

## 八、目录结构

```
mcp-client/
├── data/
│   ├── raw/                    # 原始 HTML
│   └── parsed/                 # 解析后的 JSON
├── se_kb/
│   ├── artifacts/              # 抽取的知识（按日期/域名组织）
│   ├── diagrams/
│   │   └── dfd/
│   │       ├── concepts/       # DFD 概念
│   │       ├── examples/       # DFD 示例
│   │       ├── rules/          # DFD 规则
│   │       ├── templates/      # DFD 模板
│   │       ├── validation/     # DFD 校验
│   │       └── levels/         # DFD 层次
│   ├── theory/                 # 理论知识
│   ├── mappings/               # 映射配置
│   └── schema/                 # Schema 定义
├── scripts/
│   ├── run_web_crawl.py        # 搜索+爬取脚本
│   ├── test_crawl_single.py    # 单页爬取测试
│   └── test_pipeline.py        # 流水线测试
├── extractors/                 # 抽取器模块
├── exporter_v2.py              # 主导出器
└── .env                        # 环境配置
```

---

## 九、故障排除

### 问题 1：环境变量未加载

```powershell
# 检查 .env 文件是否存在
Test-Path .env

# 手动设置环境变量（临时）
$env:FILTER_BASE_URL = "https://api.siliconflow.cn/v1"
$env:FILTER_API_KEY = "sk-xxx"
```

### 问题 2：爬取失败

```powershell
# 检查网络连接
Test-NetConnection www.google.com -Port 443

# 尝试使用代理（如果需要）
$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"
```

### 问题 3：抽取结果为空

```powershell
# 检查 parsed.json 内容
Get-Content "data/parsed/xxx.json" | ConvertFrom-Json | Select-Object title, word_count

# 查看 trace.json 了解抽取过程
Get-Content "se_kb/artifacts/.../trace.json"
```

### 问题 4：中文乱码

```powershell
# 设置 PowerShell 编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

---

*文档版本: 1.0*
*更新时间: 2024-12-09*


