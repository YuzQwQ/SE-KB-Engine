# 共享采集链实施与验收

日期：2026-10-16。变更：`unify-crawl-execution`。本报告区分已运行证据与尚未验证能力。

## 实施范围

保留 HTTPX、BeautifulSoup、Playwright、领域接口和既有 artifact 机制，没有增加爬虫框架、队列服务或依赖。Web、MCP、CLI 的页面获取已通过兼容 facade 接入同一 `CrawlService`；原独立回退编排与浏览器 helper 改为适配同一策略。

| 范围 | 实际变化 |
| --- | --- |
| 网络边界 | 按 origin 隔离凭据；每跳检查并连接已验证 IP；实际 raw/解压字节和 deadline；忽略环境代理；第三方转交与静默直连退出 |
| 获取编排 | 仅瞬态错误重试，长 Retry-After 不提前请求；成功但正文不足时最多渲染一次；最终 URL 贯穿；304 需要有效快照，默认关闭条件请求 |
| 内容 | 生产 cleaner 单次结构块遍历；H1–H6、代码空白、表格、引用、链接保留；模型输入使用同一块序列；版本 `technical-blocks-v2` |
| 存储/身份 | UUID、原子文件与最后发布 manifest；artifact 目录原子发布；URL 保留大小写路径和语义 query；v2 内容哈希保留运算符及缩进 |
| 任务 | 固定 job_id、协作取消和发布锁；有界 executor、future 回收、历史 TTL；MCP 内部调用业务服务，鉴权保留在外部工具入口 |
| 站点/浏览器 | 自动批量 robots 和 hostname 间隔；browser 专属执行器；SW/WebSocket 阻断；子请求由 verified HTTP fulfill；异常关闭策略 |

详细默认值、失败行为、配置与回滚见 [运维说明](CRAWL_AND_JOB_OPERATIONS.md)。主要实现是 `service_boundary/{fetch,transport,resolution}.py`、`se_kb_app/{services/crawl,crawling/*,jobs/*}.py`、`utils/{webpage_crawler,html_cleaner}.py`、`se_kb_app/extraction/blocks.py`。

最后补齐 MCP 知识发布分支：兼容 JSON/Markdown 与知识分类文件采用唯一批次身份及原子写入，内部调用 `_save_to_knowledge_base` 业务函数，通过有界 executor 执行，不再 await 受保护的同步工具；外部工具名、签名和鉴权保留。中文标题文件名与受限 ASCII 知识库身份分开，取消在发布前检查。相关服务/MCP 回归分别 48 项和 30 项通过。

## 已执行验证

所有目标为 MockTransport、合成文档或本机 HTTP 夹具，没有抓取外部网站、调用付费模型或启动真实浏览器。Windows 受限沙箱不能可靠执行本机通信/原子替换，完整门禁在宿主权限下执行，未降低鉴权或 URL 策略。

1. `scripts/quality.py`：编码编译、依赖漂移、安全、交付配置、文档链接、Ruff、mypy、离线检索基准及 pytest 通过。最终串行结果 **311 passed, 1 skipped, 3 deselected in 101.04s**，使用 Python 3.11.8 / HTTPX 0.28.1。三项 deselected 是新增显式 browser 验收。
2. 内容去重与浏览器子请求/拦截失败专项：**35 passed**（该次在新增 robots HTML 用例之前）。浏览器测试使用 stub，不代表 Chromium 实测。
3. `scripts/run_offline_crawl_soak.py --requests 100`：**100/100 成功**，errors 为空，最终 queued/active 均为 0，client_closed=true；queue high watermark=8。最终该次吞吐量 37.71 页/秒、P95=1006.99ms、Python traced peak=9,761,740 bytes，仅是同机夹具基线，包含并发排队，不能与旧不同脚本的数字比较为提速。见 [100 页报告](baseline/crawl-100-2026-10-16.json)。
4. `openspec validate unify-crawl-execution --strict`、文档链接和 UTF-8/编译检查通过。OpenSpec 十项实施/验收任务全部完成，未归档。

一次最终门禁遇到旧启动器 `test_actual_worker_starts_and_stops[api]` 在停止后的端口检查 `WinError 10048`（其余 310 项通过），隔离同项复跑为 1 passed/8.03s。没有修改启动器，随后串行复跑总门禁；最终结果以上面最终记录为准。

可复跑命令：

```powershell
$env:SE_KB_SKIP_DOTENV='1'
$env:NO_PROXY='localhost,127.0.0.1,::1'
.\.venv\Scripts\python.exe scripts\quality.py
.\.venv\Scripts\python.exe scripts\measure_cleaning_baseline.py
.\.venv\Scripts\python.exe scripts\run_offline_crawl_soak.py --requests 100 --report .tmp/crawl-acceptance/regression-100.json
.\.venv\Scripts\python.exe scripts\run_offline_crawl_soak.py --seconds 1800 --report .tmp/crawl-acceptance/endurance-final.json
openspec validate unify-crawl-execution --strict
```

## 内容质量语料及边界

`tests/fixtures/extraction/technical_corpus.json` 包含 50 个 CC0 合成金标准页面：十类内容模式、各五种主体容器，覆盖代码、表格、嵌套块、异常标签、中文、链接和噪声。预期正文块、代码文本、表格单元格、标题与链接均显式标注；测试调用生产 `clean_and_structure()`。

指标按预期/实际块的 multiset 计算 precision/recall，单独测重复和结构保留，没有把整页字数当准确率，也没有把完整率写死。当前合成语料全部满足 precision/recall ≥95%、必需代码和简单表格 100%、重复块 0 的门槛。

这是实现者编写、覆盖已知缺陷的合成语料，**不等于 50 个独立人工标注真实网站样本**，不能据此宣称一般网页正文质量达到 95%。最终 [清洗报告](baseline/crawl-cleaning-2026-10-16.json) precision/recall 与代码、表格、标题、链接保留均为 1.0，重复块/噪声为 0，1438.2ms/6,165,685 traced bytes。独立合法真实页语料、盲标和站点分层验收仍属上线扩展验证。

## 长时间运行证据

较早版本已有一次 1800.31 秒本机运行：30,750 次操作、无非预期结果、队列/活动为 0、client_closed=true。由于当时没有 RSS/句柄采样和代码指纹，只保留为阶段证据，不作为当前版本最终证明。

最终 [30 分钟报告](baseline/crawl-endurance-2026-10-16.json)：1800.73 秒、26,982 次操作，其中成功 17,988、预期永久失败 4,497、预期策略失败 4,497，**unexpected 为空**。关闭后 queued/active=0、client_closed=true、remaining_owned_threads=[]，关键实现 `implementation_unchanged=true`。指纹为 `202bb3f46f009447141f6b9f40bfa429d33ea0c8af8255621538155aec30ba6e`，仅覆盖脚本列出的八个采集核心文件，不是整个 dirty 工作区的 commit 身份。MCP 兼容发布分支随后单独补齐，以最终全量门禁验收，不声称该分支经过此次 soak。

记录 CPU 590.88 秒、Python traced peak=11,843,382 bytes；30 个每分钟样本 RSS=67,735,552–71,589,888 bytes、句柄=320–326，末段 RSS 约 66.4 MiB。关闭后 RSS=61,464,576 bytes、句柄=306，低于 warm 阶段的句柄数 321；初始未预热句柄数是 222，因此不能据此断言所有 OS 资源精确回归启动基线。此次证据确认已界定的 client/worker 关闭和观察窗口内的有界资源趋势。

额外执行 [五次创建/关闭周期](baseline/crawl-lifecycle-2026-10-16.json)，每次五页、共 25/25 成功；关闭后句柄为 267、275、275、275、275，没有逐周期递增。RSS 从 58,347,520 到 59,342,848 bytes，预热与分配器保留仍需和真实泄漏区分，不把 RSS 等同于未释放连接数。

P50=125ms、P95=219ms 来自最后保留的 2,048 次延迟，混合操作吞吐量 14.98/s。脚本为本机测试关闭 hostname 最小间隔，生产默认仍是 1 秒；这些数字不是生产默认吞吐量，更不是相对旧版本的加速结论。

## 明确未验证/保留的限制

- 本环境未安装 Playwright，未运行真实 Chromium 动态等待、CPU/RSS、context/page 或进程树回收测试。stub 仅证明路由失败关闭与资源关闭调用顺序。已提供默认排除的 `tests/test_crawl_browser_acceptance.py`（静态、延迟 JS 正文、永不就绪三例），仅允许测试自有 loopback origin；未来显式安装/选择浏览器后运行 `.venv/Scripts/python.exe -m pytest tests/test_crawl_browser_acceptance.py --override-ini=addopts= -m browser -q`。本轮只检查语法、类型与收集过滤，没有运行它。浏览器 POST XHR 等功能目前不支持；OS 级出口限制仍需要部署保证。
- Tor/显式代理缺少 verified adapter，采集会返回明确配置失败；不宣称已恢复匿名传输能力，也不静默直连。
- DNS 原生调用及已在途模型调用不能强杀。验证等待和网络 I/O 受 deadline 约束；原生调用可能稍后结束，DNS 线程是有界的进程级资源。模型没有真实调用验收。
- Soak 不覆盖浏览器、模型、磁盘全流水线及所有生产站点。RSS 仅本 Python 进程，不能替代将来的浏览器进程树测量。延迟统计不是五轮同机 A/B，未声明性能提升比例。
- 未实现 durable frontier/任务恢复、自动向量索引闭环、外部消息队列；业务规模没有证据要求这些能力。
- 失败的 capture/artifact staging 可留作未发布诊断，需运营按 manifest 与目录归属制定保留策略。不会自动清理用户唯一副本。
- HTTPX 私有 backend 接缝有维护风险；已用 IP/TLS/超时测试约束，升级依赖时必须复核。

## 交付与回滚

本次不提交、不归档、不暂存，不改写历史数据。开始实施前保存了 code-only 快照到忽略目录 `.tmp/crawl-preimplementation`，不包含全部用户工作区，不能整库恢复。
新采集/解析版本与 UUID 批次独立保存；回滚按入口适配器与变更 hunk 操作，网络安全修复继续保留。lxml/selectolax/trafilatura、浏览器复用、Scrapy/分布式调度仍按路线中的测量条件决定，未为追逐技术栈引入。
