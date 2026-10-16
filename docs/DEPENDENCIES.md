# 依赖与 Python 支持策略

## 支持范围

项目支持 Python 3.11、3.12 和 3.13；Python 3.11 是 `.python-version` 与 Docker 的基线。
这一范围同时写入 `pyproject.toml`、Ruff 和 mypy 配置。后续 CI 应至少覆盖 3.11 与
3.13 两个边界版本。

本次探测在无私有凭据的临时虚拟环境完成：

- Python 3.11.8：从 `requirements-prod.txt` 安装，并成功导入 MCP、HTTPX、
  ChromaDB、Flask、BeautifulSoup 和 Pillow。
- Python 3.13.2：从 `requirements.txt` 安装，并成功导入 MCP、HTTPX、
  ChromaDB、Playwright、python-docx 和 ReportLab。

## 权威声明与分组

`pyproject.toml` 是直接依赖和版本约束的唯一人工维护来源，`uv.lock` 是完整解析结果。

- 核心依赖：MCP、HTTP 客户端、搜索/HTML 清洗、模型客户端、Schema、图像和向量存储。
- `api`：Flask、CORS、Swagger 与生产 WSGI 服务。
- `browser`：Playwright 和 SOCKS 代理传输。
- `docs`：DOCX 与 PDF 生成。
- `dev` dependency group：pytest、pytest-asyncio、Ruff 和 mypy。

仓库内第三方导入已与这些声明核对。标准库、本仓库模块以及可选平台工具不写入 Python
依赖；运行时导入的可选功能必须属于相应 extra。

## 锁定、导出与漂移检查

修改依赖后执行：

```bash
uv lock
uv export --locked --no-dev --all-extras --no-emit-project --no-header -o requirements.txt
uv export --locked --no-dev --extra api --no-emit-project --no-header -o requirements-prod.txt
python scripts/check_dependencies.py
```

两个 requirements 文件是由锁文件生成的精确哈希导出，不应手工编辑。
`scripts/check_dependencies.py` 会离线检查锁文件有效性，并在临时目录重新生成两个导出进行
逐字节比较；任何失败都会保留非零退出码。

## 安装方式

开发环境通常使用 `uv sync --group dev`，按需追加 `--extra api`、`--extra browser`
或 `--extra docs`。只需要 pip 的环境可安装 `requirements.txt`；Web/API 生产或容器安装
使用更小的 `requirements-prod.txt`。
