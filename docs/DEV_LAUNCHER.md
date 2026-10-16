# 窗口开发启动器

Windows 在项目根目录双击 `启动工作台.vbs`。窗口直接使用 `.venv`，启动后不需要保持两个命令行窗口。也可从项目目录运行：

```powershell
uv sync --frozen --extra api --extra desktop --group dev
.venv\Scripts\python.exe start_launcher.py
```

默认窗口使用 pywebview + 随项目保存的 HTML/CSS/JavaScript。Windows 需要 Microsoft Edge WebView2 Runtime，通常已随 Edge 安装。界面不加载在线字体、CDN 或远程页面，也不需要启动 Web/API 服务。`desktop` extra 安装窗口所需的 Python 包，Windows 双击入口不会自动安装依赖。

如遇桌面渲染器问题，可运行 `.venv\Scripts\python.exe start_launcher.py --tk` 使用经典 Tk 窗口；这要求 Python 包含 Tkinter。Linux/macOS 使用 pywebview 对应平台的渲染器依赖。缺少桌面依赖时启动器会显示安装与回退说明。

## 使用窗口

- “全部启动”启动 Web 控制台与 REST API；也可以分别启动、停止或重启。
- Web 默认使用 `http://127.0.0.1:8000/`，REST 默认使用 `http://127.0.0.1:8001/`，API 文档位于 `/apidocs/`。服务停止后可修改端口。
- 运行状态通过 HTTP 响应确认。“打开页面”和“API 文档”只在服务就绪后打开浏览器。
- “全部 / Web / API”日志标签可分别查看输出，还可按级别和关键词筛选。取消“自动滚动”方便阅读错误。日志保存在内存，网页窗口最多保留 2000 条，经典 Tk 单栏约 3000 行；积压时优先保留新消息。
- 配置仍使用项目 `.env` 和进程环境变量。密钥无需填入启动器；浏览器控制台仍按原流程填写服务密钥。日志会脱敏已知密钥和 Bearer 凭据。
- 勾选“调试模式”后启动或重启，将启用 Flask 调试行为与详细日志。修改 Python 代码后点击重启；不自动重载。交互式网页调试器关闭，服务仅监听本机。IDE 断点调试仍使用 IDE 的 Python 调试入口。

当前前端由 Web Flask 服务渲染，不需要额外启动 Node/Vite；REST API 是另一个可独立运行的服务。Web 的知识操作调用自身的 `/api/` 路由，不依赖 REST API 的 8001 端口。

## 停止与故障处理

关闭窗口时若有服务运行，会确认停止；取消关闭会继续运行。请等采集、导出等后台任务完成后再停止，Windows 结束进程可能中断进行中的工作。启动器仅管理自己启动的进程，端口被外部进程占用时会提示更换端口或手动停止原服务。

“运行中”表示 HTTP 存活，不代表模型、向量索引等能力已配置。REST 检索可用性以 `/api/v1/ready` 为准；未配置时仍可查看日志和 API 文档。启动超过 90 秒会显示超时并保留日志，可手动停止或重启。依赖缺失时按日志运行上面的环境安装命令。没有启动任何服务时，启动器不会调用模型、抓取网页或迁移数据。

回退到旧流程只需关闭启动器并使用 `start_web.py` 或 `python -m api.app`；旧入口端口默认值保持不变。

## 验证

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_dev_launcher.py
.venv\Scripts\python.exe -m pytest -q tests/test_desktop_bridge.py
.venv\Scripts\python.exe scripts/smoke_dev_launcher.py
.venv\Scripts\python.exe scripts/smoke_web_launcher.py
uv run python scripts/quality.py
openspec validate add-desktop-dev-launcher --strict
openspec validate modernize-desktop-launcher --strict
```

专项测试包含端口冲突保护、日志脱敏与上限、进程失败、重复启动、停止与重启，以及两个真实 Flask worker 的本机 HTTP 启停；默认不访问外网或调用付费模型。

2026-10-15 验证：专项测试 13 项通过；Tk 窗口冒烟通过全部启动、调试重启、取消关闭、日志清空与全部停止。全量门禁通过（258 passed, 1 skipped），Ruff、mypy、编码编译、安全、依赖、文档与交付检查通过，OpenSpec 严格校验通过。窗口冒烟需要可用的桌面会话，单独执行，不纳入无桌面的默认测试。

网页桌面版增加 15 项桥接测试；真实 WebView2 窗口通过桥接连接、全部启动、调试重启、HTML 日志文本化、原生关闭拦截、取消退出和确认退出后的进程清理。参考 [pywebview API](https://pywebview.flowrl.com/api/) 与[无服务器桌面架构](https://pywebview.flowrl.com/guide/architecture)。

网页桌面版最终门禁：273 passed, 1 skipped；全部质量检查通过。浏览器在 1240px、860px 和 390px 宽度下验证布局；窄屏无页面横向溢出，退出弹窗可按 Escape 取消，控制台无警告和错误。
