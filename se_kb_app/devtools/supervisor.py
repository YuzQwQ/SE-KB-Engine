"""Thread-safe development process ownership, liveness and bounded output."""

from __future__ import annotations

import os
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from service_boundary.audit import configured_secrets, redact
from utils.env_loader import load_env_file

ROOT = Path(__file__).resolve().parents[2]


def validate_port(value: str | int) -> int:
    try:
        port = int(value)
    except (ValueError, TypeError) as error:
        raise ValueError("端口必须是 1024–65535 之间的整数") from error
    if not 1024 <= port <= 65535:
        raise ValueError("端口必须是 1024–65535 之间的整数")
    return port


def check_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if os.name == "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise ValueError(f"端口 {port} 已占用或不可用，请停止原服务或更换端口") from error


@dataclass(frozen=True)
class Snapshot:
    status: str
    port: int
    pid: int | None
    detail: str


class ServiceProcess:
    def __init__(self, name: str, events: queue.Queue, *, root: Path = ROOT):
        if name not in {"web", "api"}:
            raise ValueError("unknown service")
        self.name = name
        self.events = events
        self.root = root
        self._lock = threading.RLock()
        self._process: subprocess.Popen[str] | None = None
        self._status = "stopped"
        self._port = 8000 if name == "web" else 8001
        self._detail = "尚未启动"
        self._secrets: tuple[str, ...] = ()

    def snapshot(self) -> Snapshot:
        with self._lock:
            return Snapshot(self._status, self._port,
                            self._process.pid if self._process else None, self._detail)

    def emit(self, text: str) -> None:
        item = (self.name, redact(text, self._secrets)[:8192])
        try:
            self.events.put_nowait(item)
        except queue.Full:
            try:
                self.events.get_nowait()
            except queue.Empty:
                pass
            try:
                self.events.put_nowait(item)
            except queue.Full:
                pass

    def start(self, port: int, debug: bool = False) -> None:
        with self._lock:
            if self._process is not None:
                return
            self._port = validate_port(port)
            self._status, self._detail = "starting", "正在检查环境与端口"
            try:
                check_port(self._port)
                load_env_file(self.root / ".env")
                self._secrets = configured_secrets()
                environment = {**os.environ, "PYTHONUNBUFFERED": "1",
                               "PYTHONIOENCODING": "utf-8"}
                command = [sys.executable, "-u", "-m", "se_kb_app.devtools.worker",
                           self.name, "--port", str(self._port)]
                # pythonw has no console streams; children must use the console interpreter
                # with redirected pipes and CREATE_NO_WINDOW.
                python = Path(sys.executable)
                if python.name.lower() == "pythonw.exe":
                    command[0] = str(python.with_name("python.exe"))
                if debug:
                    command.append("--debug")
                process = subprocess.Popen(
                    command, cwd=self.root, env=environment, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    start_new_session=os.name != "nt",
                )
                self._process = process
                self.emit(f"启动 PID={process.pid}，http://127.0.0.1:{self._port}，"
                          f"调试={'开启' if debug else '关闭'}")
                threading.Thread(target=self._read, args=(process,), daemon=True).start()
                threading.Thread(target=self._watch, args=(process,), daemon=True).start()
            except (OSError, ValueError) as error:
                self._status, self._detail = "failed", str(error)
                self.emit(self._detail)

    def _read(self, process: subprocess.Popen[str]) -> None:
        if process.stdout:
            try:
                while chunk := process.stdout.readline(8192):
                    self.emit(chunk.rstrip())
            finally:
                process.stdout.close()

    def _watch(self, process: subprocess.Popen[str]) -> None:
        opener = build_opener(ProxyHandler({}))
        path = "/" if self.name == "web" else "/api/v1/live"
        deadline = time.monotonic() + 90
        while process.poll() is None:
            with self._lock:
                if self._process is not process or self._status == "stopping":
                    return
                starting = self._status == "starting"
                port = self._port
            if starting:
                try:
                    with opener.open(f"http://127.0.0.1:{port}{path}", timeout=0.4) as response:
                        ready = response.status == 200
                except (URLError, OSError, TimeoutError):
                    ready = False
                with self._lock:
                    if self._process is process and self._status == "starting":
                        if ready:
                            self._status, self._detail = "running", "HTTP 已响应"
                            self.emit(self._detail)
                        elif time.monotonic() >= deadline:
                            self._status = "timeout"
                            self._detail = "90 秒内未响应；查看日志，可停止或重启"
                            self.emit(self._detail)
            time.sleep(0.3)
        with self._lock:
            if self._process is process and self._status != "stopping":
                self._process = None
                self._status, self._detail = "failed", f"进程已退出，退出码 {process.returncode}"
                self.emit(self._detail)

    def stop(self) -> None:
        with self._lock:
            process = self._process
            if process is None:
                self._status, self._detail = "stopped", "已停止"
                return
            self._status, self._detail = "stopping", "正在停止进程"
        try:
            if process.poll() is None:
                if os.name == "nt":
                    result = subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW, timeout=10,
                    )
                    if result.returncode and process.poll() is None:
                        # Restricted Windows accounts can deny taskkill process
                        # enumeration while our original process handle stays valid.
                        process.terminate()
                else:
                    try:
                        getattr(os, "killpg")(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name != "nt":
                        getattr(os, "killpg")(process.pid, getattr(signal, "SIGKILL"))
                    else:
                        process.kill()
                    process.wait(timeout=5)
        except (OSError, subprocess.SubprocessError) as error:
            with self._lock:
                self._status, self._detail = "failed", f"停止失败：{error}"
            self.emit(self._detail)
            return
        with self._lock:
            self._process = None
            self._status, self._detail = "stopped", "已停止"
            self.emit(self._detail)
