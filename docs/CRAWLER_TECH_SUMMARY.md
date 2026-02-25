# 爬虫系统技术总结

## 1. 架构概述

本项目的爬虫系统采用 **"静态优先，动态回退" (Static First, Dynamic Fallback)** 的混合架构。系统旨在兼顾抓取效率与动态内容的兼容性，同时集成了完善的反爬策略、数据清洗与去重机制。

核心设计原则：
- **效率优先**：优先使用轻量级 HTTP 请求获取数据。
- **智能降级**：仅在必要时启动无头浏览器渲染动态内容。
- **数据纯净**：在入库前进行深度清洗与去重，保证知识库质量。

---

## 2. 核心组件与技术栈

### 2.1 混合抓取引擎 (Hybrid Fetcher)

- **第一阶段：静态抓取 (`httpx` + `BeautifulSoup`)**
  - 使用 `httpx` 库发送 HTTP 请求。
  - **优势**：速度极快，资源消耗低。
  - **策略**：自动处理重定向与编码识别。
  - **质量检测**：通过计算“文本密度” (Text Density) 和“主体选择器命中数” (Selector Hits) 来评估抓取质量。如果判定为动态页面（如包含 `__NUXT__`, `data-reactroot` 特征）或内容过少，则触发回退机制。

- **第二阶段：动态渲染 (`Playwright`)**
  - 使用 `Playwright` (Sync API) 启动无头浏览器。
  - **优势**：完美支持 SPA (单页应用) 和 JS 渲染内容。
  - **资源优化**：通过路由拦截 (**Request Interception**) 屏蔽广告、追踪脚本、视频流等高耗宽带资源，显著提升渲染速度。
  - **拟人化模拟**：
    - 去除 `navigator.webdriver` 等自动化指纹。
    - 随机化视口 (Viewport)、时区、语言。
    - 模拟人类行为：随机鼠标轨迹移动、非线性滚动、随机阅读停顿。

### 2.2 通用爬虫框架 (Crawler Framework)

- **模块化设计**：`CrawlerFramework` 类统一管理数据流。
- **多引擎支持**：
  - **SerpAPI**：用于 Google/Bing 等主流搜索引擎的高质量结果。
  - **DuckDuckGo**：无需 API Key 的备用搜索方案。
- **配置驱动**：所有解析规则定义在 `config/parsers/*.json` 中，无需修改代码即可适配新引擎。
- **数据分层**：
  - `data/raw`: 存储原始 JSON/HTML 响应，保留完整现场。
  - `data/parsed`: 存储提取后的结构化数据，便于后续处理。

### 2.3 智能数据清洗 (Smart HTML Cleaner)

- **多级清洗管道**：
  1. **结构化转换**：将 `<div>`, `<p>`, `<br>` 等块级元素转换为标准换行符，保留文章段落结构。
  2. **噪音过滤**：基于标签黑名单（`script`, `style`, `iframe`）和关键词黑名单（`ad-`, `copyright`, `nav`）移除干扰信息。
  3. **实体解码**：自动处理 HTML 实体编码。
  4. **规则外置**：清洗规则维护在 `config/html_cleaner_rules.json`。

### 2.4 去重系统 (Deduplication System)

基于 SQLite 本地数据库实现的双重去重机制：

1. **URL 级去重**：
   - **Normalization**：标准化 URL（转小写、移除默认端口）。
   - **参数清洗**：自动剥离 `utm_source`, `spm` 等追踪参数，避免因参数不同导致的重复抓取。
2. **内容级去重**：
   - **Content Hash**：计算正文 SHA256 哈希。
   - **SimHash 指纹**：支持基于海明距离的模糊去重（相似度阈值默认 0.85），有效识别转载或微调后的重复文章。

---

## 3. 关键技术特性总结

| 特性 | 技术实现 | 优势 |
| :--- | :--- | :--- |
| **混合抓取** | `httpx` -> `Playwright` | 兼顾 90% 的速度与 100% 的兼容性 |
| **反爬对抗** | 随机 UA、指数退避延迟、拟人化鼠标/滚动 | 突破常规反爬策略，降低被封禁风险 |
| **动态渲染** | Playwright Route Interception | 拦截广告/视频，渲染速度提升 3-5 倍 |
| **数据清洗** | 正则 + DOM 解析 + 语义黑名单 | 提取出适合 RAG 系统的纯净文本 |
| **智能去重** | URL Normalization + SimHash | 避免知识库冗余，节省向量存储空间 |

## 4. 快速上手

### 依赖安装
```bash
pip install httpx playwright beautifulsoup4 duckduckgo-search
playwright install chromium
```

### 简单调用示例
```python
from utils.webpage_crawler import WebpageCrawler

crawler = WebpageCrawler()
# 自动处理静态/动态判断
result = crawler.fetch_webpage("https://example.com/article")

if result['success']:
    print(f"Title: {result.get('title')}")
    print(f"Content Length: {len(result['content'])}")
```
