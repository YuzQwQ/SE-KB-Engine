# SE-KB: 软件工程领域知识库系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-2.0%2B-green)](https://flask.palletsprojects.com/)
[![ChromaDB](https://img.shields.io/badge/vector--db-ChromaDB-orange)](https://www.trychroma.com/)

SE-KB (Software Engineering Knowledge Base) 是一个专注于软件工程领域（特别是数据流图 DFD）的智能化知识库系统。它集成了**知识爬取**、**LLM 精炼**、**向量化存储**和**语义检索 (RAG)** 功能，旨在为下游应用（如 AI 助手、IDE 插件）提供精准的领域知识支持。

## ✨ 核心特性

*   **📚 专业的 DFD 知识体系**：内置 DFD 概念、规则、模板、案例、分层原则等结构化知识。
*   **🔍 语义检索 (RAG)**：基于 SiliconFlow Embedding 和 ChromaDB，支持意图识别（概念/规则/案例）和混合检索。
*   **🧠 智能精炼**：利用 LLM 对原始网页数据进行清洗、去重和结构化提取。
*   **🌐 灵活的 API 服务**：提供 RESTful API，支持语义搜索、系统状态监控和热重载。
*   **🚀 易于部署**：支持本地运行、Docker 部署以及 Cloudflare Tunnel 远程访问。
*   **🔌 MCP 协议支持**：兼容 Model Context Protocol，可作为 MCP Server 运行。

## 🛠️ 技术栈

*   **后端框架**: Flask
*   **向量数据库**: ChromaDB
*   **LLM 服务**: SiliconFlow API (Embedding & Chat)
*   **爬虫框架**: Playwright / SerpAPI
*   **部署**: Cloudflare Tunnel, Gunicorn

## 📂 目录结构

```
mcp-client/
├── api/                 # REST API 服务实现
│   ├── v1/              # API 版本控制
│   └── app.py           # API 入口
├── se_kb/               # 知识库数据根目录
│   ├── diagrams/        # DFD 等图表知识 (JSON)
│   ├── theory/          # 理论知识
│   ├── domain/          # 领域知识
│   └── vector_store/    # ChromaDB 向量索引文件
├── vectorizer/          # 向量化核心模块
│   ├── config.py        # 向量库配置 (Collection 定义)
│   ├── indexer.py       # 索引构建器
│   └── retriever.py     # 检索器实现
├── refiner/             # 知识精炼模块
├── scripts/             # 工具脚本
│   └── build_vector_index.py # 索引构建脚本
├── web/                 # Web 前端界面
└── requirements.txt     # 项目依赖
```

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.10+。

```bash
# 克隆仓库
git clone https://github.com/your-repo/se-kb.git
cd se-kb

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` (如果存在) 或新建 `.env` 文件，填入以下关键配置：

```ini
# .env
OPENAI_API_KEY=sk-xxxx              # 用于知识精炼的 LLM Key
EMBEDDING_API_KEY=sk-xxxx           # SiliconFlow Embedding Key
SERPAPI_API_KEY=xxxx                # SerpAPI Key (爬虫用)
KB_ADMIN_KEYS=your_admin_key_here   # API 管理员密钥
```

### 3. 构建向量索引

在启动服务前，需要先将 JSON 知识文件向量化：

```bash
python scripts/build_vector_index.py
```
*构建完成后，索引文件将存储在 `se_kb/vector_store`。*

### 4. 启动服务

**启动 API 服务 (推荐)**
```bash
python api/app.py
```
服务默认监听 `http://localhost:8000`。

**启动 Web 界面**
```bash
python start_web.py
```

## 📖 API 使用指南

服务启动后，访问 `http://localhost:8000/apidocs/` 查看完整的 Swagger 文档。

### 核心接口：语义检索

**POST** `/api/v1/search`

```json
// Request
{
    "query": "数据流图的绘制规则是什么？",
    "intent": "rule",  // 可选: concept, rule, example, template
    "top_k": 3
}
```

```json
// Response
{
    "query": "数据流图的绘制规则是什么？",
    "intent": "rule",
    "total_found": 3,
    "results": [
        {
            "content": "父图与子图的输入输出数据流必须保持一致（平衡原则）...",
            "score": 0.85,
            "source": "dfd_modeling_rules.json",
            "collection": "se_kb_dfd_rules"
        },
        ...
    ]
}
```

### 管理接口

*   `GET /api/v1/admin/stats`: 获取知识库统计信息 (需 Bearer Token)
*   `POST /api/v1/admin/reload`: 热重载向量索引 (需 Bearer Token)

## 🌐 远程访问 (Cloudflare Tunnel)

本项目内置 `cloudflared`，可快速建立安全的内网穿透，供远程调试。

```bash
# 启动 API 服务后，在从终端运行：
.\cloudflared.exe tunnel --url http://localhost:8000
```
终端将输出一个公网 HTTPS 地址（如 `https://xxxx.trycloudflare.com`），外部用户可直接通过该地址调用 API。

## 📝 开发指南

### 添加新知识
1.  将知识整理为符合 Schema 的 JSON 文件。
2.  放入 `se_kb/diagrams/dfd/` 下的对应目录（如 `concepts`, `rules`）。
3.  运行 `python scripts/build_vector_index.py` 重建索引。
4.  (可选) 调用 `/api/v1/admin/reload` 热加载。

### 扩展图表类型
如需支持 UML 或 ER 图：
1.  在 `se_kb/diagrams/` 下新建目录（如 `uml`）。
2.  修改 `vectorizer/config.py`，添加新的 Collection 定义（如 `se_kb_uml_concepts`）。
3.  重建索引。

## 📄 License

MIT License
