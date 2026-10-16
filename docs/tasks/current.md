# 当前任务：统一爬虫执行链与安全、内容、任务修复

更新时间：2026-10-16，Asia/Shanghai。用户已从只读审查转为明确要求实施《爬虫系统技术审查与优化路线》，本节优先于下方启动器历史状态。

## 当前实施事实

- OpenSpec：`openspec/changes/unify-crawl-execution`，spec-driven，**10/10 实施与验收任务完成**。用户随后授权将当前开发成果整理为一次 Git 检查点提交，具体标识以 Git 日志为准；OpenSpec 未归档。
- 页面生产入口 Web/MCP/CLI 已通过 `WebpageCrawler` facade 接入组合根创建的共享 `CrawlService`。HTTPX/BeautifulSoup/Playwright 保留；没有更换框架或引入消息队列。
- 已修复：跨 origin 凭据、策略失败回退、选定传输失败静默直连、MCP 内部重复鉴权、任务 job_id 串写/取消检查点、代码表格模型输入、块重复/代码空白、URL 语义、流式 payload、唯一原子快照与 artifact 发布。
- 新组件补齐：分类、长 Retry-After、字节/deadline、已验证 IP 连接、robots/hostname 间隔、有界 admission/history/cache、有效 304 快照、浏览器网络失败关闭。
- 最终串行完整门禁 **311 passed, 1 skipped, 3 deselected in 101.04s**；内容去重/robots/浏览器子请求/Web worker/MCP 发布回归通过。一次旧启动器端口释放 WinError 10048，隔离复跑与最终总门禁均通过，没有改启动器。100 页本机采集 **100/100 成功**，队列/活动归零、client closed；50 合成金标准生产 cleaner 达标。
- 最终 30 分钟本机混合 soak：1800.73s、26,982 次操作，unexpected={}，queued/active=0，client closed，自有 crawl/browser 线程无残留，八个采集核心文件指纹不变。MCP 兼容发布补查另以最终门禁验证，不冒称经过该 soak。五次创建/关闭周期 25/25 成功，预热后句柄稳定。报告位于 `docs/baseline/crawl-{100,cleaning,endurance,lifecycle}-2026-10-16.json`；细节与限制见 [验收记录](../CRAWL_EXECUTION_VERIFICATION.md)。

## 交付限制与下一步

- 真实 Playwright/Chromium 未安装、未启动；浏览器等待、进程树回收和 OS 出口隔离仍待显式本机浏览器验收。没有真实网站、Tor、Docker 或模型调用。
- 选定 Tor/代理在没有 verified adapter 时明确失败；这是有意收紧的能力边界，不能改回静默直连。
- 50 例是合成作者标注，不是独立真实网站人工金标准。解析引擎替换、通用提取器、浏览器复用与分布式系统按测量条件延期。
- 原生 DNS/在途模型不能强杀；进程级 DNS worker 有界，取消为协作式。未发布 staging/部分 capture 保留诊断，不自动清理用户数据。
- 当前已授权实施范围与离线验收完成，下一步可显式选择真实浏览器及独立真实网页语料验收；提交/归档仍按用户后续指令处理。保留全部既有未提交工作。操作与回滚见 [爬虫运维](../CRAWL_AND_JOB_OPERATIONS.md)。

---

# 历史任务：网页桌面开发启动器

核查日期：2026-10-16（Asia/Shanghai）。根目录：`D:/develop/MCP-develop/mcp-client`。

## 接手复核与本轮收尾（2026-10-16）

- 已重新阅读项目指令、交接、两项启动器规格以及入口、桥接、进程管理、worker 和前端轮询代码；CLI 确认两项启动器变更均为 6/6，没有待实现任务。
- Git 基线仍为 `master` / `68d1652`；接手时 tracked 修改仍为 29 文件、7266/2172 行，暂存为空。启动器主体仍未跟踪；本轮没有提交、暂存、归档或清理既有文件。
- 本轮专项测试：沙箱内 24 passed、4 failed，四项失败均为本机 HTTP 生命周期未进入 running；同一命令通过宿主权限复跑后 **28 passed in 9.78s**，支持环境限制的判断，无需改业务代码。命令：`.venv/Scripts/python.exe -m pytest -q tests/test_dev_launcher.py tests/test_desktop_bridge.py`。
- 两项 OpenSpec strict validation、JavaScript 语法、文档链接与 UTF-8 检查通过。全量门禁、GUI、浏览器视觉验证本轮未重跑，下方对应结果属于上一轮记录。
- 已补齐 README 桌面依赖安装命令和 WebView2 前置说明；已将 `openspec/config.yaml` 的旧 Python/Docker 不匹配描述改为当前支持范围与实际版本。下方“既有文档问题”记录已由本轮修正。
- 最高优先级剩余事项是用户视觉试用反馈；提交与归档仍待用户指令。跨平台、强杀回收等风险没有新增复现，不扩大功能范围。

### 交付文件边界（只读整理，不是暂存清单）

| 分组 | 路径与处理 |
| --- | --- |
| 启动器直接文件 | `start_launcher.py`、`启动工作台.vbs`、`se_kb_app/devtools/`（含 assets）、`tests/test_dev_launcher.py`、`tests/test_desktop_bridge.py`、`scripts/smoke_dev_launcher.py`、`scripts/smoke_web_launcher.py`、`docs/DEV_LAUNCHER.md`、两项启动器 `openspec/changes/` 目录。主体为 untracked，不能只审查普通 diff。 |
| 共享文件 | `README.md`、`pyproject.toml`、`uv.lock`、`requirements.txt`、`requirements-prod.txt` 含其他任务改动，未来提交需逐块审查；不能整文件视为启动器新增。 |
| 本轮文档 | 仅修改 `README.md`、`openspec/config.yaml`、`docs/tasks/current.md`、`docs/HANDOFF.md`。 |
| 依赖前置与历史工作 | 应用、鉴权边界、环境加载等大量未提交文件是现有依赖；单独提交启动器是否可运行还需核对前置提交范围。数据、output、日志、软著材料与其他历史改动不纳入启动器范围。 |

## 目标与状态

用户希望一个美观的独立窗口统一启动、停止、重启和调试前后端，避免多个终端；已明确选择 HTML/CSS + pywebview。

**事实：Windows 实现及本机验证已完成，尚未提交、归档。** 本次交接已阅读实现并重新运行验证，不以清单勾选作为唯一完成依据。下一步暂无已授权的业务功能待实现。用户最终视觉认可尚未记录。

- 已完成：原始启动器 `openspec/changes/add-desktop-dev-launcher/tasks.md` 6/6，网页桌面改造 `openspec/changes/modernize-desktop-launcher/tasks.md` 6/6；本次两者 strict validate 通过。
- 已完成：默认网页桌面、显式 `--tk` 回退、VBS 入口、独立/全部服务操作、端口验证、调试开关、日志筛选搜索、退出确认和清理。
- 部分验证：仅 Windows/Python 3.11.8/WebView2 有本次实际运行证据；其他系统和 Python 版本未复核。浏览器三种宽度的截图和旧验证记录存在，本次未重跑视觉浏览器流程。
- 未开始且非本轮验收要求：EXE 打包、自动更新、IDE 断点附加、自动代码重载、持久化窗口设置。不要自动扩大范围。

## 设计与代码地图

| 位置 | 实现与原因 |
| --- | --- |
| `start_launcher.py::main()`、`启动工作台.vbs` | 默认导入 desktop；`--tk` 按需导入旧窗口；缺依赖时显示安装/回退提示。 |
| `se_kb_app/devtools/desktop.py::render_html()` | 内嵌 `assets/index.html`、`launcher.css`、`launcher.js`，无需 Node 构建或运行中的 Web/API。 |
| `desktop.py::DesktopBridge` | `poll(cursor)`、`command(action,target,ports,debug)`、`open_service(name)`、`clear_logs()`、`cancel_exit()`、`exit()`；锁序列化操作，限制目标，关闭失败保留窗口。 |
| `supervisor.py::ServiceProcess` | 无 shell 创建子进程、验证端口、stdout/stderr 合并、脱敏、有界队列、HTTP 启动探测及停止。保留前后端独立运行。 |
| `worker.py::main()` | `web|api --port N [--debug]`；回环绑定，关闭交互调试器和自动 reloader，避免额外重载进程。 |
| `assets/launcher.js` | 非重叠 500ms 桥接轮询；端口/PID/状态更新；textContent 日志；最多 2000 条；确认退出及 Escape 取消。 |

默认 Web 8000、REST 8001；旧入口各自仍默认 8000。debug 是详细日志/Flask debug + 手动重启，不是 IDE 附加。HTTP 存活不代表 `/api/v1/ready` 检索就绪。

## 本次重新验证

- `uv run python scripts/quality.py`：**quality gate passed；273 passed, 1 skipped，37.87s**。类型、lint、编译、安全、依赖、交付和文档检查通过；检索 recall@5=1.000、MRR=0.833、NDCG=0.821、no-answer=1.000。
- `.venv/Scripts/python.exe scripts/smoke_web_launcher.py`：PASS；真实桥接、两服务启动、调试重启、HTML 日志文本化、原生关闭拦截、取消退出和最终清理。
- `.venv/Scripts/python.exe scripts/smoke_dev_launcher.py`：PASS；Tk 控件启动、调试重启、取消关闭、日志清空及停止。
- `node --check se_kb_app/devtools/assets/launcher.js` 和两项 OpenSpec strict validation：通过。
- GUI 测试使用临时项目根、临时端口、`SE_KB_SKIP_DOTENV=1`、`SKIP_SERVICE_INITIALIZATION=1`；未验证用户真实模型/向量索引/Obsidian Vault。

## 后续优先级与风险

- P1（交付前）：让用户试用并收集具体反馈；整理提交范围，不能把全工作区误当本轮修改。没有授权不要提交或归档。
- P2（待验证风险）：Windows taskkill 失败时回退 `Popen.terminate()`，未证明能清理所有孙进程；宿主强制崩溃时没有 OS Job Object 托管。`_watch()` 只检查启动存活，服务之后卡死可能仍显示 running。均不是本次已复现的阻塞 Bug。
- P2（验证范围）：跨平台、干净机器缺 WebView2 的安装流程、真实 VBS 双击与高 DPI、长时间大日志负载均未本次实测。
- 既有文档问题：README 快速安装命令未带 desktop extra（详细启动器文档正确）；OpenSpec context 仍描述 Python/Docker 版本不一致待解决，但当前 Dockerfile 已为 3.13.2。本次仅记录，不改业务或已有文档。

Git 与下一步详见 `docs/HANDOFF.md`。本次交接仅新增 `AGENTS.md`、本文件和 `docs/HANDOFF.md`。
