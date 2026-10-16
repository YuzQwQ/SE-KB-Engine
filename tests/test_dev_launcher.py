from __future__ import annotations

import queue
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from se_kb_app.devtools import supervisor


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_status(service, status: str) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if service.snapshot().status == status:
            return
        time.sleep(0.05)
    pytest.fail(f"Expected {status}, got {service.snapshot()}")


@pytest.mark.parametrize("port", ["abc", "", "1023", "65536", "8000; whoami"])
def test_reject_invalid_ports(port):
    with pytest.raises(ValueError):
        supervisor.validate_port(port)


def test_occupied_port_preserves_external_listener(tmp_path: Path):
    events: queue.Queue = queue.Queue(maxsize=10)
    service = supervisor.ServiceProcess("web", events, root=tmp_path)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        service.start(listener.getsockname()[1])
        assert service.snapshot().status == "failed"
        assert service.snapshot().pid is None
        service.stop()
        assert listener.fileno() != -1


def test_bounded_log_redacts_secrets_and_bearer():
    events = queue.Queue(maxsize=2)
    service = supervisor.ServiceProcess("web", events)
    service._secrets = ("private-test-key-123",)
    for _ in range(10):
        service.emit("private-test-key-123 Bearer token-value")
    assert events.qsize() == 2
    while not events.empty():
        _, line = events.get_nowait()
        assert "private-test-key" not in line
        assert "token-value" not in line


@pytest.mark.parametrize("name", ["web", "api"])
def test_lifecycle_liveness_duplicate_and_restart(monkeypatch, tmp_path: Path, name):
    original_popen = subprocess.Popen
    calls = []

    def local_http(command, **kwargs):
        calls.append(command)
        port = command[command.index("--port") + 1]
        code = (
            "from http.server import HTTPServer, BaseHTTPRequestHandler\n"
            "class Handler(BaseHTTPRequestHandler):\n"
            " def do_GET(self):\n"
            "  self.send_response(200); self.end_headers(); self.wfile.write(b'ok')\n"
            f"HTTPServer(('127.0.0.1', {port}), Handler).serve_forever()\n"
        )
        return original_popen([sys.executable, "-u", "-c", code], **kwargs)

    monkeypatch.setattr(supervisor.subprocess, "Popen", local_http)
    # Windows taskkill also uses Popen internally; retain its original command.
    def spawn(command, **kwargs):
        if command[0] == "taskkill":
            return original_popen(command, **kwargs)
        return local_http(command, **kwargs)

    monkeypatch.setattr(supervisor.subprocess, "Popen", spawn)
    service = supervisor.ServiceProcess(name, queue.Queue(maxsize=100), root=tmp_path)
    try:
        port = free_port()
        service.start(port, debug=True)
        wait_status(service, "running")
        first_pid = service.snapshot().pid
        service.start(port)
        assert len(calls) == 1
        assert "--debug" in calls[0]
        service.stop()
        assert service.snapshot().status == "stopped"
        supervisor.check_port(port)
        service.start(free_port())
        wait_status(service, "running")
        assert service.snapshot().pid != first_pid
    finally:
        service.stop()
    assert service.snapshot().pid is None


def test_failed_spawn_is_reported(monkeypatch, tmp_path: Path):
    def fail(*args, **kwargs):
        raise OSError("interpreter unavailable")

    monkeypatch.setattr(supervisor.subprocess, "Popen", fail)
    service = supervisor.ServiceProcess("web", queue.Queue(maxsize=10), root=tmp_path)
    service.start(free_port())
    assert service.snapshot().status == "failed"
    assert "interpreter unavailable" in service.snapshot().detail


def test_unexpected_exit_preserves_diagnostics(monkeypatch, tmp_path: Path):
    original_popen = subprocess.Popen

    def failing_process(command, **kwargs):
        return original_popen([sys.executable, "-u", "-c",
                               "print('startup failed'); raise SystemExit(7)"], **kwargs)

    monkeypatch.setattr(supervisor.subprocess, "Popen", failing_process)
    events: queue.Queue = queue.Queue(maxsize=100)
    service = supervisor.ServiceProcess("api", events, root=tmp_path)
    service.start(free_port())
    wait_status(service, "failed")
    assert "7" in service.snapshot().detail
    assert service.snapshot().pid is None
    deadline = time.monotonic() + 2
    lines = []
    while time.monotonic() < deadline:
        try:
            lines.append(events.get(timeout=0.1)[1])
        except queue.Empty:
            pass
        if any("startup failed" in line for line in lines):
            break
    assert any("startup failed" in line for line in lines)


@pytest.mark.integration
@pytest.mark.parametrize("name", ["web", "api"])
def test_actual_worker_starts_and_stops(monkeypatch, tmp_path: Path, name):
    monkeypatch.setenv("SE_KB_SKIP_DOTENV", "1")
    monkeypatch.setenv("SE_KB_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("SKIP_SERVICE_INITIALIZATION", "1")
    monkeypatch.setenv("KB_READ_KEYS", "test-launcher-read")
    monkeypatch.setenv("KB_ADMIN_KEYS", "test-launcher-admin")
    service = supervisor.ServiceProcess(name, queue.Queue(maxsize=200))
    port = free_port()
    try:
        service.start(port)
        wait_status(service, "running")
    finally:
        service.stop()
    assert service.snapshot().pid is None
    supervisor.check_port(port)
