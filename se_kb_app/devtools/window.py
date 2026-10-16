"""Tk desktop console for the two local Flask services."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from functools import partial
from tkinter import messagebox, scrolledtext, ttk

from se_kb_app.devtools.supervisor import ROOT, ServiceProcess, validate_port

STATUS = {"stopped": "已停止", "starting": "启动中", "running": "运行中",
          "stopping": "停止中", "failed": "异常", "timeout": "启动超时"}


class LauncherWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("SE-KB · 开发工作台")
        root.geometry("1040x740")
        root.minsize(820, 600)
        root.configure(background="#111827")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#111827")
        style.configure("TLabel", background="#111827", foreground="#e5e7eb",
                        font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 22, "bold"))
        style.configure("Muted.TLabel", foreground="#9ca3af")
        style.configure("TButton", padding=(12, 7), font=("Microsoft YaHei UI", 10))
        style.configure("TCheckbutton", background="#111827", foreground="#e5e7eb")
        style.map("TCheckbutton", background=[("active", "#1f2937")])
        self.events: queue.Queue = queue.Queue(maxsize=2000)
        self.services = {name: ServiceProcess(name, self.events) for name in ("web", "api")}
        self.ports = {"web": tk.StringVar(value="8000"), "api": tk.StringVar(value="8001")}
        self.states: dict[str, tk.StringVar] = {}
        self.entries: dict[str, ttk.Entry] = {}
        self.service_buttons: dict[str, list[ttk.Button]] = {}
        self.debug = tk.BooleanVar(value=False)
        self.busy = threading.Event()
        self.closing = False
        self.log_views: dict[str, scrolledtext.ScrolledText] = {}
        self._build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.timer = root.after(120, self._tick)

    def _build(self) -> None:
        content = ttk.Frame(self.root, padding=24)
        content.pack(fill="both", expand=True)
        ttk.Label(content, text="SE-KB 开发工作台", style="Title.TLabel").pack(anchor="w")
        ttk.Label(content, text="前端与 API，一处启动 · 实时诊断 · 独立重启",
                  style="Muted.TLabel").pack(anchor="w", pady=(5, 20))
        toolbar = ttk.Frame(content)
        toolbar.pack(fill="x", pady=(0, 16))
        self.all_buttons = []
        for label, action in (("▶ 全部启动", "start"), ("↻ 全部重启", "restart"),
                              ("■ 全部停止", "stop")):
            button = ttk.Button(toolbar, text=label,
                                command=partial(self.action, action, ("web", "api")))
            button.pack(side="left", padx=(0, 8))
            self.all_buttons.append(button)
        ttk.Checkbutton(toolbar, text="调试模式（重启后生效）", variable=self.debug).pack(side="right")
        for name, title, subtitle in (
            ("web", "Web 控制台", "页面、知识采集、精炼、知识图谱"),
            ("api", "REST API", "检索接口与 API 文档 /apidocs/"),
        ):
            card = ttk.Frame(content, padding=12, relief="groove", borderwidth=1)
            card.pack(fill="x", pady=(0, 12))
            heading = ttk.Frame(card)
            heading.pack(fill="x")
            ttk.Label(heading, text=title, font=("Microsoft YaHei UI", 12, "bold")).pack(side="left")
            ttk.Label(heading, text="  " + subtitle, style="Muted.TLabel").pack(side="left")
            row = ttk.Frame(card)
            row.pack(fill="x", pady=(10, 5))
            ttk.Label(row, text="127.0.0.1 :").pack(side="left")
            entry = ttk.Entry(row, textvariable=self.ports[name], width=7)
            entry.pack(side="left", padx=(5, 12))
            self.entries[name] = entry
            self.service_buttons[name] = []
            for label, action in (("启动", "start"), ("重启", "restart"), ("停止", "stop")):
                button = ttk.Button(row, text=label,
                                    command=partial(self.action, action, (name,)))
                button.pack(side="left", padx=3)
                self.service_buttons[name].append(button)
            ttk.Button(row, text="打开页面" if name == "web" else "API 文档",
                       command=partial(self.open_page, name)).pack(side="right")
            self.states[name] = tk.StringVar(value="已停止 · 尚未启动")
            ttk.Label(card, textvariable=self.states[name], style="Muted.TLabel",
                      wraplength=920).pack(anchor="w", pady=(4, 0))
        log_header = ttk.Frame(content)
        log_header.pack(fill="x", pady=(6, 8))
        ttk.Label(log_header, text="运行日志", font=("Microsoft YaHei UI", 12, "bold")).pack(side="left")
        ttk.Button(log_header, text="清空日志", command=self.clear_logs).pack(side="right")
        self.follow = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_header, text="自动滚动", variable=self.follow).pack(side="right", padx=12)
        notebook = ttk.Notebook(content)
        notebook.pack(fill="both", expand=True)
        for key, title in (("all", "全部"), ("web", "Web"), ("api", "API")):
            view = scrolledtext.ScrolledText(
                notebook, wrap="word", background="#080f1c", foreground="#d1fae5",
                insertbackground="white", font=("Consolas", 10), relief="flat",
                state="disabled", height=10,
            )
            notebook.add(view, text=title)
            self.log_views[key] = view
        ttk.Label(content, text="仅本机开发服务 · 修改代码后点重启 · API 存活不代表检索配置就绪",
                  style="Muted.TLabel").pack(anchor="w", pady=(12, 0))
        ttk.Label(content, text=str(ROOT), style="Muted.TLabel").pack(anchor="w", pady=(3, 0))

    def action(self, action: str, names: tuple[str, ...]) -> None:
        if self.busy.is_set() or self.closing:
            return
        ports: dict[str, int] = {}
        if action != "stop":
            try:
                ports = {name: validate_port(self.ports[name].get()) for name in self.services}
                if len(set(ports.values())) != len(ports):
                    raise ValueError("Web 和 API 必须使用不同端口")
            except ValueError as error:
                messagebox.showerror("检查端口", str(error), parent=self.root)
                return
        debug = self.debug.get()
        self.busy.set()

        def work() -> None:
            try:
                for name in names:
                    service = self.services[name]
                    if action in {"stop", "restart"}:
                        service.stop()
                    if action in {"start", "restart"}:
                        service.start(ports[name], debug)
            except Exception as error:
                self.services[names[0]].emit(f"操作失败：{error}")
            finally:
                self.busy.clear()

        threading.Thread(target=work, daemon=True).start()

    def open_page(self, name: str) -> None:
        state = self.services[name].snapshot()
        if state.status != "running":
            messagebox.showinfo("服务尚未就绪", "请先启动服务，等待 HTTP 响应。", parent=self.root)
            return
        suffix = "/" if name == "web" else "/apidocs/"
        threading.Thread(target=webbrowser.open,
                         args=(f"http://127.0.0.1:{state.port}{suffix}",), daemon=True).start()

    def clear_logs(self) -> None:
        for view in self.log_views.values():
            view.configure(state="normal")
            view.delete("1.0", "end")
            view.configure(state="disabled")

    def _tick(self) -> None:
        for name, service in self.services.items():
            state = service.snapshot()
            pid = f" · PID {state.pid}" if state.pid else ""
            self.states[name].set(f"{STATUS[state.status]}{pid} · {state.detail}")
            self.entries[name].configure(state="disabled" if state.pid or self.busy.is_set() else "normal")
            for index, button in enumerate(self.service_buttons[name]):
                disabled = self.busy.is_set() or self.closing
                if index == 0:
                    disabled = disabled or state.pid is not None
                if index == 2:
                    disabled = disabled or state.pid is None
                button.configure(state="disabled" if disabled else "normal")
        for button in self.all_buttons:
            button.configure(state="disabled" if self.busy.is_set() or self.closing else "normal")
        batches: dict[str, list[str]] = {key: [] for key in self.log_views}
        for _ in range(150):
            try:
                name, line = self.events.get_nowait()
            except queue.Empty:
                break
            text = f"{datetime.now():%H:%M:%S} [{name.upper()}] {line}\n"
            batches["all"].append(text)
            batches[name].append(text)
        for key, lines in batches.items():
            if not lines:
                continue
            view = self.log_views[key]
            view.configure(state="normal")
            view.insert("end", "".join(lines))
            line_count = int(view.index("end-1c").split(".")[0])
            if line_count > 3000:
                view.delete("1.0", f"{line_count - 3000}.0")
            if self.follow.get():
                view.see("end")
            view.configure(state="disabled")
        if self.closing and not self.busy.is_set():
            if any(service.snapshot().pid is not None for service in self.services.values()):
                self.closing = False
                messagebox.showerror("停止失败", "有服务尚未退出，请查看日志后重试关闭。", parent=self.root)
            else:
                self.root.destroy()
                return
        self.timer = self.root.after(120, self._tick)

    def close(self) -> None:
        if self.closing:
            return
        if self.busy.is_set():
            messagebox.showinfo("正在处理", "请等待当前操作完成后再关闭。", parent=self.root)
            return
        active = any(service.snapshot().pid for service in self.services.values())
        if active and not messagebox.askokcancel(
            "退出开发工作台", "关闭将停止本窗口启动的服务，并中断正在执行的任务。继续？", parent=self.root,
        ):
            return
        self.action("stop", ("web", "api"))
        self.closing = True


def main() -> None:
    root = tk.Tk()
    LauncherWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
