# SE-KB-Engine

SE-KB-Engine 是一个用于技术知识库构建的搜索、抓取、清洗、结构化抽取、版本化落盘与检索系统。项目提供彼此独立的 MCP、REST、Web 和离线脚本入口；默认质量流程完全离线，不调用付费模型。

## 支持范围

- Python 3.11、3.12、3.13；本地和容器推荐 3.13。
- Windows 与 Linux 必需 CI。
- HTTP 抓取，按策略回退 Playwright；可选代理/Tor。
- 结构化抽取、版本化 artifact、完整性扫描与 copy-only 迁移。
- Chroma 兼容入口与离线 BM25/vector/hybrid 检索评测。
- Bearer 角色鉴权、CSRF、SSRF 边界、限流、任务取消和关联诊断。
- 可选 Obsidian Vault 投影、冲突保护、知识关系图与 JSON Canvas 输出。

## 目录与架构

```text
api/                 REST API（Flask，默认 8000）
web/                 Web 控制台（单独启动，默认 8000）
server.py            MCP stdio 服务
se_kb_app/           应用、领域、任务、抓取、artifact、抽取与检索核心
service_boundary/    鉴权、输入、URL/fetch、安全错误与审计边界
vectorizer/          现有 Chroma 分块、索引和查询适配器
scripts/             离线质量、扫描、迁移、评测和运维命令
schemas/             artifact、抽取、检索与索引 JSON Schema
deploy/              容器、Compose 与 Nginx 配置
tests/                默认断网的单元、集成、契约和安全测试
openspec/             主规格与变更历史
```

运行时依赖方向为 `入口/适配器 → application/domain ← infrastructure`。配置和拥有生命周期的资源由 `se_kb_app.composition.Application` 组装。详见 [架构说明](docs/ARCHITECTURE.md)。

## 离线快速开始

安装 [uv](https://docs.astral.sh/uv/) 后：

```powershell
uv sync --frozen --extra api --group dev
uv run python scripts/quality.py
```

质量命令执行编码/编译、锁文件漂移、离线安全、Ruff、mypy、离线检索基准和 182+ 个默认断网测试。它不需要 API key。

## 服务入口

推荐本地开发使用窗口启动器。先安装桌面依赖：

```powershell
uv sync --frozen --extra api --extra desktop --group dev
```

Windows 双击根目录 `启动工作台.vbs`，或运行 `.venv\Scripts\python.exe start_launcher.py`。可一键启动 Web（8000）与 REST API（8001）、查看日志和分别重启；Windows 还需 WebView2 Runtime，详见[窗口开发启动器](docs/DEV_LAUNCHER.md)。

先复制 `.env.example` 的非秘密配置，并用进程环境或秘密管理器提供长随机密钥。不要提交 `.env`。

REST API（`http://127.0.0.1:8000`）：

```powershell
$env:KB_READ_KEYS='replace-with-random-read-key'
$env:KB_ADMIN_KEYS='replace-with-random-admin-key'
uv run python -m api.app
```

Web 控制台（也使用 8000，不能与 REST 同时占用同一地址）：

```powershell
uv run python start_web.py
```

MCP 是 stdio 服务，由 MCP 客户端启动，不监听 HTTP 端口：

```powershell
uv run python server.py
```

`/api/v1/live` 只表示进程响应；`/api/v1/ready` 检查必需检索能力；详细诊断在需要 admin bearer 的 `/api/v1/admin/diagnostics`。

## 容器

容器默认非 root、只读根文件系统，数据/缓存/输出/日志/索引使用独立卷，密钥从启动环境注入：

```powershell
$env:KB_READ_KEYS='replace-with-random-read-key'
$env:KB_ADMIN_KEYS='replace-with-random-admin-key'
docker compose -f deploy/docker-compose.yml up --build kb-api
```

网关是显式 profile，默认只绑定回环地址的 8080；公网/TLS 必须在部署前另行配置和验证：

```powershell
docker compose -f deploy/docker-compose.yml --profile gateway up --build
```

参见 [容器与回滚](docs/CONTAINER_OPERATIONS.md)。本项目不会自动公开部署、删除旧索引或迁移唯一数据副本。

## 网络、费用与数据写入

- 默认质量和检索评测：无网络、无模型费用，只写临时目录或明确的报告目标。
- 搜索、抓取、浏览器、Tor 和真实模型测试：可能访问外网；LLM/embedding 可能收费，必须显式选择对应 pytest marker 或脚本。
- artifact 迁移默认 dry-run；`--execute` 只允许在审核了精确源/目标后使用。
- 索引构建默认 dry-run，新索引验证后才可原子切换，旧索引不会自动删除。

详细说明见 [测试分层](docs/TESTING.md)、[安全边界](docs/SECURITY.md)、[artifact 生命周期](docs/ARTIFACT_LIFECYCLE.md) 和 [检索评测](docs/RETRIEVAL_EVALUATION.md)。

## 运维与发布

- [配置参考](docs/SETTINGS.md)
- [Obsidian Vault 集成](docs/OBSIDIAN_INTEGRATION.md)
- [REST/MCP 契约与副作用](docs/INTERFACES.md)
- [故障处理手册](docs/RUNBOOKS.md)
- [发布流程](docs/RELEASE_PROCESS.md)
- [供应链分诊](docs/SUPPLY_CHAIN_TRIAGE.md)

版本的唯一来源是 `pyproject.toml` 中的 `[project].version`。发布前必须完成 `docs/RELEASE_READINESS.md` 的证据清单。

## License

MIT License
