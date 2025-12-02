# Crawler Core 导出包使用指南

本包提取了项目中的核心爬虫能力，便于单独分发与使用：
- 静态抓取：使用 `httpx` 获取 HTML。
- 解析清洗：使用 `BeautifulSoup` 清洗并提取正文、标题、图片。
- 质量评估与回退：动态指纹与正文密度判断，必要时使用 Playwright 渲染；最后兜底 `r.jina.ai` 纯文本。
- 可选图片文本化：统一视觉模型接口，输出 `ocr`、`description`、`dfd`（默认关闭）。
- 文件输出：保存到 `data/raw` 与 `data/parsed` 两类 JSON。

## 目录结构

```
export/crawler_core/
├── README.md
├── requirements.txt
├── config/
│   └── html_cleaner_rules.json           # 可选：站点清洗规则（示例）
├── data/
│   ├── raw/
│   └── parsed/
├── scripts/
│   └── run_crawl.py                      # 命令行示例：爬取并保存
└── utils/
    ├── html_cleaner_core.py
    ├── image_analyzer_core.py            # 可选：视觉模型（默认返回空结果）
    ├── playwright_fetcher_core.py
    └── webpage_crawler_core.py
```

## 环境准备

- Python 3.9+（建议 3.10+）
- 安装依赖：

```
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

- 可选：启用动态渲染（对 SPA/懒加载页面更稳）

```
playwright install chromium
```

### 关于大模型 API 与 .env

- 核心爬虫（httpx+bs4）不依赖任何大模型 API。
- 仅当你启用图片文本化（`--images`）时，才会调用远端视觉模型接口（HTTP 或 SiliconFlow）。
- 为方便配置，本包支持在根目录放置 `.env` 文件（示例见 `.env.example`），脚本会自动读取环境变量。

## 快速开始

运行单页抓取并保存结果：

```
python scripts/run_crawl.py "https://www.w3cschool.cn/software-engineering/analysis-design-tools.html"
```

可选启用图片文本化（需要配置远端视觉模型）：

```
python scripts/run_crawl.py "<URL>" --images
```

在 PowerShell 中（Windows），也可直接设置环境变量运行：

```
$env:VISUAL_MODEL_PROVIDER = "siliconflow"
$env:VISUAL_MODEL_API_KEY = "<你的Key>"
$env:VISUAL_MODEL = "<你的模型名>"
python scripts/run_crawl.py "<URL>" --images
```

完成后，输出文件位于：
- `data/raw/<domain>_<title>_<timestamp>.json`
- `data/parsed/<domain>_<title>_parsed_<timestamp>.json`

## 结果说明

- 原始抓取（raw）：
  - 字段：`url`、`status_code`、`headers`、`content`（HTML 或文本）、`encoding`、`timestamp`、`source`（httpx/playwright/r.jina.ai）
- 解析结果（parsed）：
  - 核心字段：`title`、`source_url`、`clean_text`、`markdown`、`images`、`word_count`、`parsed_at`
  - 指标字段：`metrics`（`html_length`、`cleaned_length`、`text_density`、`main_selector_hits`、`dynamic_markers_found`、`fallback_used` 等）
  - 图片文本化：若启用，`images` 的每项包含 `alt`、`title`、`ocr`、`description`、`dfd`。

## 视觉模型（可选）

默认不启用视觉模型。若使用 `--images`：
- HTTP 适配器：在运行时传入 `{"provider":"http","endpoint":"...","api_key":"..."}`。
- SiliconFlow 适配器：在运行时传入 `{"provider":"siliconflow","base_url":"https://api.siliconflow.cn/v1","api_key":"<KEY>","model":"<MODEL>"}`。

提示词：本地适配器内置提示词，统一输出为 JSON，仅包含 `ocr[]`、`description`、`dfd|null`。

环境变量（可用 `.env` 或 `$env:`）：

```
# 选择提供方（其一）
VISUAL_MODEL_PROVIDER=siliconflow
# 或
VISUAL_MODEL_PROVIDER=http

# SiliconFlow（示例）
VISUAL_MODEL_BASE_URL=https://api.siliconflow.cn/v1
VISUAL_MODEL_API_KEY=sk-xxxx
VISUAL_MODEL=Qwen2.5-VL-7B-Instruct
VISUAL_MODEL_TIMEOUT=60

# HTTP（示例）
VISUAL_MODEL_ENDPOINT=https://your-vision-api.example.com/infer
VISUAL_MODEL_API_KEY=token-xxxx
VISUAL_MODEL_TIMEOUT=30
VISUAL_MODEL_REQ_URL_FIELD=image_url
VISUAL_MODEL_REQ_B64_FIELD=image_base64
VISUAL_MODEL_REQ_TASKS_FIELD=tasks
VISUAL_MODEL_RESP_OCR_FIELD=ocr
VISUAL_MODEL_RESP_DESCRIPTION_FIELD=description
VISUAL_MODEL_RESP_DFD_FIELD=dfd
```

## 人类行为模拟（低成本）

目的：降低被动/主动反爬的概率，让动态渲染更接近真实用户行为（不保证完全绕过）。

- Playwright 动态渲染：
  - 禁用 `AutomationControlled`（浏览器启动参数）。
  - 在页面初始化时移除 `navigator.webdriver` 标记并补齐常见属性（`window.chrome`、`languages`、`plugins`）。
  - 随机 `User-Agent`、视口、语言、时区。
  - 自动滚动使用随机步长与停顿；模拟鼠标随机移动；停留时间随机且至少 7 秒。
- httpx 静态抓取：
  - 轻量随机延时（0.4–1.6s）。
  - 随机 `User-Agent` 与 `Accept-Language`（可关闭）。

环境变量（默认开启，置为 `0`/`false` 关闭）：

```
# Playwright 人类行为模拟（回退渲染时生效）
PLAYWRIGHT_HUMAN_SIM=1
# 停留时长（秒），仅在 PLAYWRIGHT_HUMAN_SIM=1 时使用
HUMAN_SIM_MIN_DWELL_SEC=7
HUMAN_SIM_MAX_DWELL_SEC=12

# httpx 静态抓取的随机 UA/语言
HTTPX_RANDOM_UA=1
```

注意：上述策略为“低成本”通用方案，无法保证绕过特定站点的复杂风控。必要时建议配合代理、真实浏览器（非 headless）、更强的指纹模拟。

## 代理池支持（可选）

为提升稳定性与降低风控命中率，本包支持简单代理池：静态请求与 Playwright 渲染均可使用代理，并可按请求轮换。

- 启用方式：在 `.env` 中设置（如果仅设置 `PROXY_URL`，无需开启 `PROXY_POOL_ENABLED`）

```
PROXY_POOL_ENABLED=1
PROXY_POOL_FILE=config/proxies.txt
# 或者仅使用单一代理（设置该值将直接生效并覆盖文件清单）
PROXY_URL=http://127.0.0.1:7890
# 每次静态请求是否轮换代理（默认 1）
PROXY_ROTATE_PER_REQUEST=1
```

- 代理格式（每行一个）：
  - `http://host:port`
  - `http://user:pass@host:port`
  - `socks5://host:port`（需要 `httpx-socks`，已在 `requirements.txt` 中列出）

- 文件位置：`config/proxies.txt`（相对 `export/crawler_core/` 路径），示例：

```
# one per line
http://127.0.0.1:7890
socks5://127.0.0.1:9050
http://user:pass@proxy.example.com:8080
```

- Playwright：若代理可用，会以 `proxy={'server': <proxy>}` 启动 Chromium。
- httpx：若为 `socks5://` 代理，使用 `httpx_socks.SyncProxyTransport`；若不可用则自动回退为直连。

## 清洗规则

`config/html_cleaner_rules.json` 可添加站点专用选择器：

```json
{
  "csdn.net": {
    "main_selectors": ["#content_views", ".article_content", "article"],
    "exclude_keywords": ["logo", "icon", "sprite", "ad"]
  }
}
```

未命中站点规则时，会使用通用选择器（`article`、`main`、`#content` 等）抽取主体。

## Fallback 回退策略

1. 首选 `httpx` 静态抓取。
2. 若正文长度过短、密度低或命中动态指纹，则尝试 `Playwright` 渲染。
3. 若渲染不可用或失败，则兜底 `https://r.jina.ai/<URL>` 纯文本。

## 常见问题

- 报错 `playwright not installed`：不影响静态抓取与代理兜底；如需动态渲染，执行 `playwright install chromium`。
- 解析结果过短：可能是 SPA/懒加载页面，建议启用动态渲染。
- 图片文本化无输出：未启用或未配置远端视觉模型；请传入 `--images` 并提供选项。

## 二次开发建议

- 在 `utils/html_cleaner_core.py` 增加站点自定义解析策略。
- 在 `utils/image_analyzer_core.py` 扩展更多视觉服务或本地 OCR。
- 在 `utils/webpage_crawler_core.py` 调整 `_should_fallback` 阈值以适配不同站点。

## 许可证

本导出包为内部功能提取示例，不含开源许可证声明。分发前请遵守相关站点的使用条款与爬取规范。