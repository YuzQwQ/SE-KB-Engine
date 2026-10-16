"""Bundled desktop shell and narrow, validated pywebview bridge."""

from __future__ import annotations

import queue
import threading
import webbrowser
from collections import deque
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from se_kb_app.devtools.supervisor import ServiceProcess, validate_port

ASSETS = Path(__file__).with_name("assets")


def render_html() -> str:
    html = (ASSETS / "index.html").read_text(encoding="utf-8")
    css = (ASSETS / "launcher.css").read_text(encoding="utf-8")
    js = (ASSETS / "launcher.js").read_text(encoding="utf-8")
    return html.replace('<link rel="stylesheet" href="launcher.css">', f"<style>{css}</style>").replace(
        '<script src="launcher.js"></script>', f"<script>{js}</script>"
    )


class DesktopBridge:
    def __init__(self) -> None:
        self._events: queue.Queue = queue.Queue(maxsize=2000)
        self._services = {name: ServiceProcess(name, self._events) for name in ("web", "api")}
        self._operation = threading.Lock()
        self._logs_lock = threading.Lock()
        self._logs: deque[dict[str, Any]] = deque(maxlen=2000)
        self._sequence = 0
        self._window: Any = None
        self._close_requested = False
        self._allow_close = False

    def poll(self, cursor: int = 0) -> dict:
        if type(cursor) is not int or cursor < 0:
            cursor = 0
        with self._logs_lock:
            for _ in range(300):
                try:
                    name, text = self._events.get_nowait()
                except queue.Empty:
                    break
                self._sequence += 1
                lower = text.lower()
                level = "error" if any(word in lower for word in (
                    "error", "traceback", "failed", "失败", "异常",
                )) else "warning" if any(word in lower for word in (
                    "warning", "warn", "警告", "超时",
                )) else "info"
                self._logs.append({"id": self._sequence, "source": name, "text": text,
                                   "time": datetime.now().strftime("%H:%M:%S"), "level": level})
            logs = [row for row in self._logs if row["id"] > cursor][:300]
            next_cursor = logs[-1]["id"] if logs else max(cursor, self._sequence)
        return {"services": {name: asdict(s.snapshot()) for name, s in self._services.items()},
                "busy": self._operation.locked(), "logs": logs, "cursor": next_cursor,
                "close_requested": self._close_requested}

    def command(self, action: str, target: str, ports: dict | None = None,
                debug: bool = False) -> dict:
        if action not in ("start", "stop", "restart") or target not in ("all", "web", "api"):
            return {"ok": False, "error": "未知的服务操作"}
        if type(debug) is not bool:
            return {"ok": False, "error": "调试选项必须为布尔值"}
        parsed = {}
        if action != "stop":
            try:
                if not isinstance(ports, dict) or set(ports) != {"web", "api"}:
                    raise ValueError("请提供 Web 和 API 端口")
                for name, value in ports.items():
                    if type(value) not in (str, int):
                        raise ValueError("端口必须是整数")
                    parsed[name] = validate_port(value)
                if parsed["web"] == parsed["api"]:
                    raise ValueError("Web 和 API 必须使用不同端口")
            except ValueError as error:
                return {"ok": False, "error": str(error)}
        if not self._operation.acquire(blocking=False):
            return {"ok": False, "error": "正在处理其他操作，请稍候"}
        try:
            if self._allow_close:
                return {"ok": False, "error": "窗口正在退出"}
            names = ("web", "api") if target == "all" else (target,)
            errors = []
            for name in names:
                service = self._services[name]
                if action in ("stop", "restart"):
                    service.stop()
                    if service.snapshot().pid is not None:
                        errors.append(service.snapshot().detail)
                        continue
                if action in ("start", "restart"):
                    service.start(parsed[name], debug)
                if service.snapshot().status == "failed":
                    errors.append(service.snapshot().detail)
            return {"ok": not errors, "error": "；".join(errors)}
        finally:
            self._operation.release()

    def open_service(self, name: str) -> dict:
        if name not in ("web", "api"):
            return {"ok": False, "error": "未知服务"}
        state = self._services[name].snapshot()
        if state.status != "running":
            return {"ok": False, "error": "服务尚未就绪，请先启动并等待 HTTP 响应"}
        suffix = "/" if name == "web" else "/apidocs/"
        opened = webbrowser.open(f"http://127.0.0.1:{state.port}{suffix}")
        return {"ok": bool(opened), "error": "" if opened else "未找到可用浏览器"}

    def clear_logs(self) -> dict:
        with self._logs_lock:
            self._logs.clear()
            for _ in range(2000):
                try:
                    self._events.get_nowait()
                except queue.Empty:
                    break
        return {"ok": True}

    def cancel_exit(self) -> dict:
        self._close_requested = False
        return {"ok": True}

    def exit(self) -> dict:
        if not self._operation.acquire(blocking=False):
            return {"ok": False, "error": "操作尚未完成，请稍后退出"}
        try:
            if not self._cleanup():
                return {"ok": False, "error": "有服务停止失败，请查看日志后重试"}
            self._allow_close = True
            if self._window:
                self._window.destroy()
            return {"ok": True}
        finally:
            self._operation.release()

    def _cleanup(self) -> bool:
        for service in self._services.values():
            service.stop()
        return not any(s.snapshot().pid is not None for s in self._services.values())

    def _on_closing(self) -> bool:
        if self._allow_close:
            return True
        if self._operation.locked() or any(s.snapshot().pid for s in self._services.values()):
            self._close_requested = True
            return False
        self._allow_close = True
        return True


def main() -> None:
    import webview

    bridge = DesktopBridge()
    window = webview.create_window(
        "SE-KB · 开发工作台", html=render_html(), js_api=bridge,
        width=1240, height=850, min_size=(860, 640), background_color="#0b0e14",
        text_select=True,
    )
    if window is None:
        raise RuntimeError("桌面窗口创建失败")
    bridge._window = window
    window.events.closing += bridge._on_closing
    try:
        # Edge Chromium is the Windows default; no external page or HTTP control port.
        webview.start(private_mode=True, debug=False)
    finally:
        bridge._cleanup()
