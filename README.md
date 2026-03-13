# SE-KB-Engine

一个用于 **知识库构建的智能爬取与信息抽取引擎**。

SE-KB-Engine 提供从 **搜索 → 抓取 → 清洗 → 知识抽取 → 数据落盘** 的完整流水线，
用于自动化收集技术资料并构建结构化知识库。

项目最初用于个人知识库构建实验，目前仍在持续开发中。

---

## ✨ Features

- 🔍 **搜索驱动抓取**
  - 通过搜索接口获取候选网页
  - 自动批量抓取相关内容

- ⚡ **混合抓取策略**
  - HTTPX 静态抓取，高性能处理普通网页
  - Playwright 动态回退，兼容依赖 JavaScript 渲染的页面

- 🧹 **内容清洗**
  - 使用 BeautifulSoup 提取正文
  - 去除广告、导航栏等无关内容

- 🧠 **LLM 知识抽取**
  - 基于 MCP + LLM API 进行结构化信息抽取
  - 输出 JSON / Markdown 等知识产物

- 📊 **任务管理 Web 控制台**
  - 基于 Flask + JavaScript
  - 支持 URL 抓取、批量任务、进度监控与结果管理

- 🗂 **数据管理**
  - 基于 SQLite 实现 URL 去重
  - 支持历史记录管理

- 🐳 **部署友好**
  - 支持 Docker 部署
  - 支持 Nginx + Gunicorn
  - 可选代理 / Tor / SOCKS5 增强网络鲁棒性

---

## 🏗 Architecture

整体流程：

```text
Search
  ↓
URL Queue
  ↓
Crawler
  ↓
Content Cleaner
  ↓
LLM Extractor
  ↓
Knowledge Artifacts
```

核心模块示意：

```text
se-kb-engine/
│
├─ crawler/        # 抓取模块
├─ extractor/      # LLM 抽取模块
├─ pipeline/       # 数据处理流水线
├─ web/            # Flask 控制台
├─ database/       # SQLite 管理
└─ scripts/        # 工具脚本
```

---

## 🚀 Quick Start

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

### 3. 打开 Web 控制台

```text
http://localhost:5000
```

---

## ⚙ Tech Stack

- Python 3
- Flask
- SQLite
- HTTPX
- BeautifulSoup
- Playwright
- MCP (Model Context Protocol)
- OpenAI / OpenRouter / DeepSeek
- Docker
- Nginx
- Gunicorn

---

## 📌 Use Cases

- 构建技术知识库
- 自动整理技术博客与文档
- 为 AI Agent 提供知识数据源
- 生成 RAG 所需的数据集

---

## 🖼 Screenshot

你可以在这里放项目界面截图：

```markdown
![Web Console](docs/images/web-ui.png)
```

---

## 📄 Example Output

结构化抽取结果示例：

```json
{
  "title": "Transformer Attention Explained",
  "summary": "本文介绍了注意力机制的基本原理及其在 Transformer 中的作用。",
  "concepts": ["attention", "softmax", "transformer"],
  "source": "https://example.com/article"
}
```

---

## 📈 Roadmap

- [ ] 自动质量评分
- [ ] 更稳定的反爬策略
- [ ] 向量数据库集成
- [ ] RAG Pipeline 支持
- [ ] 更完善的任务调度与可观测性

**Backend**

- Python 3
- Flask
- SQLite

**Web Crawling**

- HTTPX
- BeautifulSoup
- Playwright

**LLM Integration**

- MCP (Model Context Protocol)
- OpenAI / OpenRouter / DeepSeek APIs

**Deployment**

- Docker
- Nginx
- Gunicorn

---

## 📜 License

MIT License
