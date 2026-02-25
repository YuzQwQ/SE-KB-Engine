# 项目目录结构说明

为减少顶层目录数量并提升可维护性，本项目目录结构进行了归类与简化。以下为主要目录与用途说明：

## 顶层目录
- `config/` 配置文件与系统提示、格式模板、解析器配置等
- `docs/` 项目文档（运行指南、网络代理说明、结构说明等）
- `data/` 数据目录（爬取的原始与解析结果）
  - `raw/` 原始响应与中间结果（示例：`requirement_analysis_crawl_result*.json`）
  - `parsed/` 解析后的结构化数据（JSON/Markdown等）
- `scripts/` 数据与知识处理脚本（如通用知识处理器、格式处理器）
- `utils/` 通用工具与爬虫框架（`crawler_framework.py` 等）
- `se_kb/` 领域知识库素材与规则、映射、示例等
- `src/` 代码模块（若有子模块或包结构，可在此统一管理）
- `experimental/` 归档的探索性或尚未启用的目录（`distributed/`、`intelligent/`）
- `logs/` 运行日志
- 顶层入口：`server.py`、`client.py`

## 已完成的结构变更
- 创建 `docs/` 并迁移根目录说明文档至其中
- 创建 `data/raw` 与 `data/parsed`，并将历史爬取结果迁移到 `data/raw`
- 统一解析器配置路径到 `config/parsers`，并同步更新爬虫框架默认路径
- 归档空目录 `distributed/` 与 `intelligent/` 到 `experimental/` 下，减少顶层目录数量

## 运行与约定
- 入口脚本仍位于顶层，保持无破坏式改动：
  - 启动后端：`python server.py`
  - 启动前端（网页客户端）：`python start_web.py`
- 解析器配置载入默认从 `config/parsers` 路径读取
- 数据写入位置默认在 `data/` 下的 `raw` 与 `parsed`

## 后续建议（可选）
- 若后续将 `utils/` 合并到 `src/`，请同步更新导入路径与 `path_config.py`
- `se_kb/` 如需统一归档到 `data/`，建议在代码中明确其消费路径后再进行迁移
