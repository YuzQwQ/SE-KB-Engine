# Coding Agent 交接

## 最新：required-ci 六矩阵失败修复（2026-10-16）

用户报告推送后 run `38893926368` 全红。已通过 GitHub 连接读取六份日志，确认三类原因：Linux mypy 不认识未受 sys.platform 条件保护的 Windows-only 属性；Linux 端口探测把 TIME_WAIT 当活动监听；Windows coverage 未继承 quality 子进程 UTF-8 环境，编码 CLI 输出崩溃。此前“端口失败只是环境波动”的推断不再适用于该 Linux 缺陷。

修复位于 `.github/workflows/ci.yml`、`scripts/check_encodings.py`、`se_kb_app/{crawling/resources,services/tor,devtools/supervisor}.py` 和两个测试文件。保留 Windows 独占端口策略，POSIX 只启用 SO_REUSEADDR、不启用 SO_REUSEPORT；活动 listener 仍被回归测试保护，停止检查区分 listener 与 TCP 残留，并在 POSIX 验证同端口重启。CLI 明确输出 UTF-8；全部 CI 步骤共享 offline/UTF-8 job 环境。

当前本机专项 28 passed/1 skipped、Linux 平台全项目 mypy 通过、总门禁 314 passed/2 skipped/3 deselected；强制 cp1252 的 coverage 同为 314 passed/2 skipped/3 deselected。远端六矩阵验证收尾中。OpenSpec 追加任务 5.1–5.3，前两项完成、最后一项待远端实测。所有历史输出、软著、本机截图仍保留且不提交。

---

## 最新任务：统一采集链实施（2026-10-16）

本节取代下方“本轮未改业务代码”“没有已授权业务功能”的旧启动器交接结论。用户已明确授权实施爬虫审查路线。

后续提交指令：用户已授权把当前开发成果提交为一次 Git 检查点，具体标识以 Git 日志为准。本机截图、运行输出和生成的软著材料保留在工作区，不纳入该提交；OpenSpec 不归档。下方“未提交”记录描述的是实施结束时的历史状态。

- 变更目录：`openspec/changes/unify-crawl-execution`，**10/10 完成，未归档**。先读 [当前任务](tasks/current.md)、[运维](CRAWL_AND_JOB_OPERATIONS.md) 和 [验收证据](CRAWL_EXECUTION_VERIFICATION.md)，不要仅依据旧审查中的行号或旧组件测试推断生产入口。
- 真实页面链：Web/MCP/CLI → `WebpageCrawler` facade → `CrawlService` → robots/容量 → 状态机 → verified HTTP/至多一次 browser → production cleaner blocks → 独立快照/已有 extraction/artifact。组合根已注入 crawl；standalone fallback 是进程 singleton，owned resource 由组装根/atexit 关闭。
- 关键修改在 `service_boundary/{fetch,transport,resolution,decoding,html_policy}.py`、`se_kb_app/crawling/`、`services/crawl.py`、`jobs/`、`extraction/blocks.py`、`utils/{webpage_crawler,html_cleaner,web_deduplication,webpage_storage}.py`、`extractors/pipeline.py`、`writers/artifacts_writer.py`、`server.py`、`web/{app,services}.py`。旧第三方回退和重复浏览器编排退出；没有新增框架/依赖。
- 最终串行门禁 **311 passed/1 skipped/3 deselected in 101.04s**；一次旧启动器 WinError 10048 已隔离复跑通过，最终全量也通过，未改启动器。100 页共享服务回归全成功；50 合成技术页达标。30 分钟 26,982 次混合操作无非预期结果，核心指纹不变、队列/活动归零、client closed、自有 worker 无残留；五次创建/关闭周期也通过。报告在 `docs/baseline/crawl-{100,cleaning,endurance,lifecycle}-2026-10-16.json`。MCP 最后补齐的兼容发布、内部知识保存与 `scripts/format_processor.py` 原子写入以最终门禁验收，不声称它们运行在核心 soak 中。
- 浏览器仅 stub 验证，真实 Playwright 未安装。Tor/代理没有 verified adapter，返回 `crawl_transport_unavailable`，不得默默直连。原生 DNS 与在途模型不能强杀，取消为有界等待/协作检查点。未发布 staging 保留，不能批量清理。
- 开始实施时已有大量 dirty/untracked 内容；HEAD `68d1652`，初始 tracked 29 文件/7266 增/2172 删，暂存为空。code-only 快照在忽略目录 `.tmp/crawl-preimplementation`（不是完整备份，尤其不含 writer/tests）；最终变更混合先前工作，禁止整库 reset/clean/暂存。没有提交、归档或删除用户唯一副本。

---

核查：2026-10-16，Asia/Shanghai。仓库根目录 `D:/develop/MCP-develop/mcp-client`。先读根目录 `AGENTS.md` 和 `docs/tasks/current.md`。

标记约定：**事实**＝本次从文件、Git 或实际执行核实；**历史记录**＝持久文件中记载、未本次重跑；**待验证/推测**＝尚无复现证据。

## 最新接手复核（2026-10-16，优先于下方旧轮次状态）

- 已对照当前代码、OpenSpec CLI 和 Git：启动器功能清单仍为两项各 6/6；HEAD 与接手时 tracked diff 统计均符合原交接，暂存区为空。
- 本轮未改业务代码。已补齐 README 的桌面依赖安装/WebView2 说明，并修正 `openspec/config.yaml` 仍称 Docker 3.10 的过时背景。实际 `.python-version` 是 3.11、Docker 是 3.13.2，均在支持范围内。
- 两个启动器测试文件在沙箱中为 24 passed、4 failed（本机 HTTP 生命周期停在 starting）；相同命令经宿主权限复跑为 **28 passed in 9.78s**。因此没有把沙箱失败当产品缺陷修复。两项 strict validation、JS 语法、文档链接、UTF-8 检查均通过。
- 下方全量门禁、GUI smoke、浏览器截图仍是上一轮证据，本轮没有重跑，也没有新增用户视觉验收结论。
- 已在 `docs/tasks/current.md` 整理直接文件、共享文件和历史依赖的交付边界。当前任务没有可直接继续实现的遗漏功能；下一步需要用户视觉反馈，提交/归档仍需用户指令。
- 本轮仅编辑 `README.md`、`openspec/config.yaml` 和这两份任务交接文档；保留全部既有工作区内容，未暂存、提交、归档或启动用户真实服务。

## 1. 当前任务与最终验收

用户已要求并同意把统一前后端窗口启动器升级为 HTML/CSS + pywebview 的精致桌面控制台。验收标准：独立窗口在服务停止时可打开；默认 Web 8000、REST 8001；支持单独/全部启动停止重启、端口修改、debug、运行状态和日志筛选；关闭可取消且确认后清理拥有的进程；端口冲突不杀外部服务；无需两个终端，VBS 入口保持可用，Tk 可显式回退。

**事实：Windows 实现和当前验证已完成；没有已授权而遗漏的功能。** 用户尚未明确给出成品视觉验收结论。当前请求仅是上下文交接，不能据此重写业务、提交或丢弃改动。

## 2. 已完成与准确代码位置

所有下列路径均相对仓库根目录。

| 文件 | 入口/接口与职责 |
| --- | --- |
| `start_launcher.py` | `main()`：默认网页桌面、`--tk` 回退；缺依赖/渲染器异常时提示。 |
| `启动工作台.vbs` | 通过项目 `.venv/Scripts/pythonw.exe` 启动，无需终端；不自动装包。 |
| `se_kb_app/devtools/desktop.py` | `render_html()` 内联资源；`main()` 创建 1240×850 窗口，最小 860×640；连接关闭事件。 |
| 同上 `DesktopBridge` | `poll(cursor=0)` 返回 services/busy/logs/cursor/close_requested；`command(action,target,ports,debug)` 验证并执行；`open_service(name)` 只打开固定回环地址；`clear_logs()`、`cancel_exit()`、`exit()`；`_on_closing()` 处理原生关闭。 |
| `se_kb_app/devtools/supervisor.py` | `validate_port()`、`check_port()`；`ServiceProcess.start/stop/snapshot/emit/_read/_watch` 管进程、端口、UTF-8 日志、脱敏、HTTP 启动探测。 |
| `se_kb_app/devtools/worker.py` | `main()` 参数 `web|api --port N [--debug]`，Flask loopback 开发服务。 |
| `se_kb_app/devtools/window.py` | `LauncherWindow`，原 Tk 实现保持可用。 |
| `se_kb_app/devtools/assets/index.html`、`launcher.css`、`launcher.js` | 深色侧栏、服务卡片、状态、响应式日志区、来源/级别/搜索、调试开关、退出对话框；JS 为闭包内 command/poll/renderState/renderLogs。 |
| `tests/test_dev_launcher.py`、`tests/test_desktop_bridge.py` | 分别 13 项进程测试与 15 项桥接测试，包含真实 worker 和验证失败/并发/清理保护。 |
| `scripts/smoke_dev_launcher.py`、`scripts/smoke_web_launcher.py` | 显式 GUI 冒烟，本机临时端口/数据。 |
| `pyproject.toml`、`uv.lock`、`requirements*.txt` | desktop extra `pywebview>=6,<7`；本机实际安装 6.2.1。生产 requirements 只包含 api extra。 |
| `docs/DEV_LAUNCHER.md` | 用户使用、安装、验证与回退说明。 |

OpenSpec：`openspec/changes/add-desktop-dev-launcher/` 和 `openspec/changes/modernize-desktop-launcher/`，各有 proposal/design/specs/tasks，均 6/6，strict validate 已本次复核；**仍为未归档 change**。此前 `integrate-obsidian-vault` 84/84、`productionize-observability-and-delivery` 31/31 也显示 complete，但本次没有逐文件审计那两项，不要推断都已提交或归档。

## 3. 尚未完成与优先级

- **P1，交付核对**：用户主观视觉认可没有记录；提交边界未整理，未提交、未归档。不要在没有指令时自动完成 Git/OpenSpec 发布动作。
- **P2，验证欠账**：跨平台/其他 Python 版本、干净系统安装 WebView2、实际 VBS 双击、高 DPI 和长时间日志负载未本次验证。
- **P2，可靠性探索**：验证强制关闭宿主和 taskkill 失败时孙进程的回收，以及 HTTP 运行后卡死的状态处理；先复现再另开修复，不把推测写成已发生 Bug。
- **未开始且不属于原验收**：EXE 打包、自动更新、设置持久化、IDE 断点附加、自动代码重载。没有需求不要扩展。

## 4. 关键架构决策与原因

- 前端是 Flask 模板，不是 Node/Vite；Web `/api/` 属于 Web 本身，REST 8001 是独立入口。启动器分端口解决原先两个旧入口都默认 8000 的冲突。
- pywebview 只承载内联本地资源；不创建 HTTP 进程控制服务器，不加载远程页面/CDN/字体，使启动器独立于受管服务。CSP 含 `connect-src 'none'`；bridge 暴露方法应保持小而受限。
- 复用 `ServiceProcess`，UI 通过锁串行化受管操作，通过异步非重叠轮询刷新；不把 Tk 业务复制进 HTML。已知队列/日志各有上限，动态数据用 textContent。
- debug 启用 Flask debug 和详细日志，但 `use_reloader=False`、`use_debugger=False`，通过手动重启加载代码，减少重载子进程和交互调试器风险。不是 IDE 附加调试。
- 原生 closing 事件有活动进程时返回 False，再由 HTML 对话框处理；停止失败不销毁窗口。UI 无服务时关闭不必确认。
- `desktop` 为可选 extra，不强制进入生产容器；`--tk` 提供回退。不要为 UI 使用本机实际密钥作为测试夹具。

## 5. 已尝试但未采用/失败的方案

- **事实**：Tk 是已完成的前一版，仍在 `window.py`；用户提出外观要求后选择网页桌面。它不是功能失败，不应删除来“清理旧实现”。
- **实现注释证据，未本次故障注入**：Windows 受限账户可能拒绝 taskkill 的进程枚举；`ServiceProcess.stop()` 已加入用原始 Popen 句柄 terminate 的回退。不能据此宣称进程树回收已全覆盖。
- **历史记录/无法独立复核**：开发期间曾遇 Playwright file:// 被拒及沙箱 npx/DNS 访问失败；对应原始失败日志未整理为项目报告。本机静态 HTTP 预览用于后续截图，不能把该预览端口当产品依赖。当前复核不需要重走安装或外网流程。
- 本次交接执行的完整检查及两项 GUI 冒烟没有失败，不改业务代码来制造或掩盖问题。

## 6. Bug、风险与未解决信息

**事实/实现限制：**

- `_watch()` 只在 starting 时探测 HTTP；进入 running 后主要检测进程退出，不是持续健康监控。90 秒 timeout 后没有自动恢复探测。
- Windows 正常停止用 `taskkill /PID <owned pid> /T /F`；失败回退仅终止直接子进程。停止会中断进行中的采集/导出；确认不是任务级优雅取消。
- GUI smoke 和真实 worker 测试均设置 `SKIP_SERVICE_INITIALIZATION=1`，不能证明用户模型、向量索引、检索 readiness 或 Obsidian 真库可用。
- README 的通用快速安装命令只含 api extra，桌面安装应按 `docs/DEV_LAUNCHER.md` 加 desktop。`openspec/config.yaml` 中“修复 Python/Docker 不匹配”是旧背景；当前 `deploy/Dockerfile` 实际为 Python 3.13.2。
- CSS 压缩为长行，暂未引入构建工具；修改时注意两组响应式覆盖。未做 EXE 分发。

**待验证/推测：**宿主被强杀可能遗留 worker；无 Windows Job Object；高负载全量重绘 2000 条日志的长期性能、clear_logs 与在途 poll 的竞态未专项压测。没有本次复现的阻塞 Bug，不得直接当成已确诊故障。

本次只读进程/端口查询未列出 pythonw 窗口或 8000/8001/18996 监听；这是查询结果，不是对所有会话的运行保证。浏览器的 localhost 地址属于环境快照，不能证明服务存活；不要沿用历史 PID 终止进程。

## 7. Git 工作区与未提交修改

**事实（新增交接文件之前）：**分支 `master`，HEAD `68d1652`（2026-04-07 20:09:59 +0800，Merge branch master）；最近 `c7e639c` 为环境变量加载重构、`88592d1` 更新 README。针对启动器路径没有相关新提交；它们是 untracked 文件。

`git diff --cached --stat` 为空。tracked 修改 **29 文件**；`git diff --stat` 为 **7266 insertions / 2172 deletions**，不包含 untracked；`git ls-files --others --exclude-standard` 为 **397 文件**，porcelain 全量 **426 项**。本次再新增 3 份交接文档，数量会相应增加；这些数字不代表只做了启动器。

tracked 修改完整分组：

```text
.gitignore  .python-version  README.md  pyproject.toml  uv.lock
requirements.txt  requirements-prod.txt
api/app.py  api/auth.py  api/v1/admin.py  api/v1/search.py
client.py  registry.py  server.py  start_web.py
deploy/Dockerfile  deploy/docker-compose.yml  deploy/nginx.conf
scripts/query_knowledge.py
utils/env_loader.py  utils/playwright_fetcher.py
utils/webpage_crawler.py  utils/webpage_storage.py  vectorizer/config.py
web/app.py  web/services.py  web/static/script.js
web/static/style.css  web/templates/index.html
```

untracked 含 `.codex/`、`.github/`、`openspec/`、`se_kb_app/`、`service_boundary/`、`tests/`、大量 docs/scripts/schemas、`output/`、`.playwright-cli/`、启动器入口等。不要只看普通 git diff 判断范围，也不要整库 git add。`requirements.txt` 被 Git 显示为二进制 diff；本次 UTF-8 和依赖一致性检查通过，不等于应手工重写它。

本轮启动器直接涉及上述代码地图、新增 `desktop` extra/lock/exports、README 的启动入口说明，以及相关 docs/OpenSpec；其余大量变更来自更早任务，作者和逐项归属无法由当前 HEAD 自动还原。

**本次交接只新增**：`AGENTS.md`、`docs/tasks/current.md`、`docs/HANDOFF.md`。无业务修改、提交、暂存、归档或丢弃。

写入后复查：tracked diff 仍为原来的 29 文件、7266/2172 行，暂存区仍为空，porcelain 从 426 增至 429 项，正好新增上述三份文件；三份文件 UTF-8 检查及文档检查通过。

## 8. 测试、结果与验证边界

以下于 2026-10-16 **重新执行**，不是仅引用聊天或旧清单：

| 命令（项目根目录执行） | 实际结果 |
| --- | --- |
| `uv run python scripts/quality.py` | quality gate passed；**273 passed, 1 skipped，37.87s**。编码编译 640 文本/237 Python；依赖漂移、安全、交付、文档、Ruff、mypy 均通过。mypy 有现有未标注函数提示，无错误。 |
| `.venv/Scripts/python.exe scripts/smoke_web_launcher.py` | PASS：真实 WebView2 桥接、全部启动、调试重启替换 PID、HTML 日志文本化、原生关闭/取消、确认退出和清理。 |
| `.venv/Scripts/python.exe scripts/smoke_dev_launcher.py` | PASS：Tk 控件、两服务启动、debug 重启、取消关闭、日志清空、全部停止。 |
| `node --check se_kb_app/devtools/assets/launcher.js` | 通过。 |
| `.venv/Scripts/python.exe -m pytest -q -rs tests/test_obsidian_foundations.py` | 15 passed, 1 skipped；明确返回 `symbolic links are unavailable on this host`，用于核对跳过原因。 |
| `openspec validate add-desktop-dev-launcher --strict` | valid。 |
| `openspec validate modernize-desktop-launcher --strict` | valid。 |

全量 pytest 包含两个启动器测试文件；本次未单独重跑其 13/15 项子集。唯一 skip 对应 Windows 符号链接不可用的 Vault 路径测试（`tests/test_obsidian_foundations.py` 的 skip 分支）；未验证有符号链接权限时的表现。离线检索基准：recall@5=1.000、MRR=0.833、NDCG=0.821、no-answer=1.000。

本机 Python **3.11.8**、pywebview **6.2.1**。测试使用临时目录和本机随机端口；受限沙箱可能阻断 localhost/进程枚举，实际 GUI/全量测试通过宿主权限机制运行。不要为了让测试通过放开业务鉴权或读真实 `.env`。

**历史持久证据，未本次重跑：** `docs/DEV_LAUNCHER.md` 记录 1240/860/390px、Escape、控制台检查；截图位于 `output/playwright/.playwright-cli/page-2026-10-15T14-21-57-675Z.png`（桌面）及 `page-2026-10-15T14-22-27-299Z.png`（窄屏），同目录 yml 可读。静态预览按钮故意禁用，不能代替真实 bridge 测试。截图不应被当成 UI 自动断言报告。

未验证事项见第 3、6 节，尤其真实检索/模型/真库、跨平台和强杀清理。

## 9. 下一任 Agent 的前三步

1. 在项目根目录读 `AGENTS.md`、`docs/tasks/current.md` 和两项启动器 OpenSpec design/spec；运行 `git status --short` 与 `git diff --stat` 核对工作区，记住启动器主体仍是 untracked。保留全部既有修改。
2. 用 `.venv/Scripts/python.exe start_launcher.py` 展示当前网页桌面（环境缺依赖才按 `docs/DEV_LAUNCHER.md` 安装），根据用户实际反馈确定继续优化点。先只读检查 8000/8001 占用；不得直接结束外部服务，也不要重复跑已通过的整套门禁来代替任务判断。
3. 有新修复需求时先用最小用例复现第 6 节相关风险，再更新相应 OpenSpec/`current.md`、修改与该需求直接相关的代码并跑专项测试；若用户要求收尾提交或归档，先审查精确文件范围并显式包含新增文件，不能把 29 个 tracked 修改与所有 untracked 一起提交。
