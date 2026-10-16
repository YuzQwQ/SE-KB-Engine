# 项目开发约定

## 架构与入口

- SE-KB-Engine 是 Python 知识采集、清洗、抽取、版本化 artifact、索引与检索项目。架构参考 `docs/ARCHITECTURE.md`。
- 依赖方向：入口/适配器 → application/domain ← infrastructure。`se_kb_app/domain.py` 不依赖 Flask、MCP 或第三方网络、模型、向量 SDK；应用服务不要直接依赖入口框架。
- `se_kb_app/settings.py::AppSettings.from_sources()` 负责类型化配置；`se_kb_app/composition.py::ApplicationBuilder` 与 `Application` 管理资源组装、惰性创建和关闭。保留兼容入口，逐步迁移。
- `server.py` 为 MCP stdio；`api/app.py::create_app()` 为 REST；`web/app.py` 为 Flask Web 控制台。前端是 `web/templates/` 与 `web/static/`，没有独立 Node/Vite 服务。
- 桌面入口 `start_launcher.py` 默认运行 `se_kb_app/devtools/desktop.py`（pywebview）；`--tk` 使用 `window.py`。HTML/CSS/JS 位于 `se_kb_app/devtools/assets/`；进程管理复用 `supervisor.py::ServiceProcess`，子服务通过 `worker.py` 启动。
- 启动器默认 Web 8000、REST 8001，只监听回环。独立旧入口默认均为 8000，不要混淆。Web 自身的 `/api/` 不依赖 REST 8001。

## 配置、数据和安全

- 不泄露 `.env`、API key、cookies、代理凭据；日志复用 `service_boundary/audit.py` 的脱敏。鉴权与输入边界集中于 `service_boundary/`。
- 保留用户数据、向量库、artifact、日志、生成的软著材料和无关工作区改动。不要为清理任务执行批量还原、删除或整库暂存。
- Obsidian 集成见 `docs/OBSIDIAN_INTEGRATION.md`：默认关闭，只管理自己的命名空间；人工修改、未知目标和陈旧笔记采用保护策略。
- 桌面桥接只允许固定服务/操作和验证后的端口；不要加入任意命令执行、远程特权页面或未鉴权 HTTP 控制端口。日志用文本节点渲染。只停止启动器自己拥有的进程。
- 外网、付费模型、Tor、浏览器和 Docker 测试需显式选择；默认验证不可触发真实抓取或付费调用。

## 工具与验证

- `pyproject.toml` 是版本、依赖和工具配置来源，支持 Python >=3.11,<3.14；`.python-version` 与容器版本分别以当前文件为准。
- 准备桌面开发环境：`uv sync --frozen --extra api --extra desktop --group dev`。变更依赖需同步 `uv.lock` 和生成的 requirements。
- `requirements.txt` 导出全部 extras，`requirements-prod.txt` 只导出 api：使用 `uv export --locked --no-dev --all-extras --no-emit-project --no-header --quiet --output-file requirements.txt`；生产文件将 `--all-extras` 换为 `--extra api`。
- 总门禁：`uv run python scripts/quality.py`，包括编码编译、依赖漂移、安全、交付、文档、Ruff、mypy、离线检索基准和 pytest。遵循现有 marker、架构和契约测试。
- 窗口冒烟独立运行：`scripts/smoke_web_launcher.py` 和 `scripts/smoke_dev_launcher.py`，需要桌面会话；默认 pytest 不包含 GUI 冒烟。
- Windows 受限执行环境可能阻断 localhost 父子进程通信或进程枚举；区分运行环境限制与产品缺陷，按宿主权限机制处理，不关闭鉴权来绕过。
- 遵循 `.editorconfig`、`.gitattributes` 和 pyproject 中的 Ruff/mypy 配置：UTF-8，Python 四空格，常规源文件 LF，PowerShell CRLF；避免无关格式重写。

## 规划与交接

- 项目使用 repo-local OpenSpec（`openspec/config.yaml`）。涉及已有变更时先检查 CLI 状态、规格与任务文件；完成实现后执行 strict validate。是否归档或提交按用户请求处理。
- 临时进度与未解决问题维护在 `docs/tasks/current.md`，上下文交接见 `docs/HANDOFF.md`。不要把短期状态或聊天摘要追加到本文件。
