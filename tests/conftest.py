"""pytest 全局 fixtures。

原则（对应 backlog TEST-004/005/006）：
- 测试不得写入真实 data/、se_kb/、output/、shared_data/；
- 测试修改的环境变量必须在结束后恢复；
- 需要固定行为的测试使用 frozen_time/frozen_uuid 风格的显式注入，不做全局 monkeypatch。
"""
from __future__ import annotations

import ipaddress
import random
import socket
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def env_guard(monkeypatch: pytest.MonkeyPatch):
    """提供进程环境变量隔离。

    用法:
        def test_x(env_guard):
            env_guard.setenv("FOO", "bar")
            ...

    monkeypatch 会在测试结束后自动恢复原值；未通过 monkeypatch 的
    os.environ 直接修改是禁止的（code review 检查点）。
    """
    return monkeypatch


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch):
    """清空与本项目相关的关键环境变量，模拟"未配置"环境。

    用于测试配置加载的默认值与降级路径，避免开发者本机 .env 影响结果。
    """
    project_vars = [
        "OPENAI_API_KEY", "BASE_URL", "MODEL", "FILTER_MODEL_ID", "KB_MODEL_ID",
        "MERGE_MODEL_ID", "EMBEDDING_MODEL_ID", "VISUAL_MODEL",
        "USE_TOR", "TOR_EXECUTABLE_PATH", "TOR_PASSWORD",
        "SERPAPI_KEY", "DUCKDUCKGO_BACKEND",
        "ENABLE_URL_DEDUP", "ENABLE_CONTENT_DEDUP", "URL_CACHE_DAYS",
        "KB_READ_KEYS", "KB_ADMIN_KEYS", "API_DEBUG", "CORS_ORIGINS",
        "SE_KB_SKIP_DOTENV",
    ]
    for var in project_vars:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.fixture(autouse=True)
def block_external_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """默认阻断进程内网络；显式 network/browser/tor/llm 测试除外。"""
    external_marks = {"network", "browser", "tor", "llm"}
    if external_marks.intersection(request.node.keywords):
        return

    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection

    def is_loopback(address) -> bool:
        if not isinstance(address, tuple) or not address:
            return True
        host = address[0]
        if host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def guarded_connect(sock, address):
        if not is_loopback(address):
            raise RuntimeError("External network is disabled for offline tests")
        return original_connect(sock, address)

    def guarded_create_connection(address, *args, **kwargs):
        if not is_loopback(address):
            raise RuntimeError("External network is disabled for offline tests")
        return original_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


@pytest.fixture
def isolated_data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把约定的数据根指向临时目录。"""
    root = tmp_path / "workspace"
    for name in ("data", "se_kb", "output", "logs", "cache"):
        (root / name).mkdir(parents=True)
    monkeypatch.chdir(root)
    monkeypatch.setenv("SE_KB_SKIP_DOTENV", "1")
    return root


@dataclass(frozen=True)
class FrozenSources:
    now: datetime
    uuid: uuid.UUID
    seed: int


@pytest.fixture
def frozen_sources() -> FrozenSources:
    """供支持显式注入的代码使用的稳定时间、UUID 和随机种子。"""
    seed = 20260915
    random.seed(seed)
    return FrozenSources(
        now=datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc),
        uuid=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        seed=seed,
    )


@pytest.fixture
def fake_http_response():
    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def json(self):
            return {"ok": True}

        def raise_for_status(self):
            return None

    return FakeResponse()


@pytest.fixture
def fake_model_client():
    class FakeModelClient:
        calls: list[dict] = []

        def complete(self, **kwargs):
            self.calls.append(kwargs)
            return {"result": "fixture"}

    return FakeModelClient()


@pytest.fixture
def api_client(isolated_data_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KB_READ_KEYS", "test-read-key")
    monkeypatch.setenv("KB_ADMIN_KEYS", "test-admin-key")
    monkeypatch.setenv("SKIP_SERVICE_INITIALIZATION", "1")
    from api.app import create_app

    application = create_app(initialize_services=False)
    application.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
    return application.test_client()


@pytest.fixture
def web_client(isolated_data_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KB_READ_KEYS", "test-read-key")
    monkeypatch.setenv("KB_ADMIN_KEYS", "test-admin-key")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost")
    from web.app import app

    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture
def web_admin_headers(web_client):
    web_client.get("/")
    cookie = web_client.get_cookie("kb_csrf")
    assert cookie is not None
    return {
        "Authorization": "Bearer test-admin-key",
        "Origin": "http://localhost",
        "X-CSRF-Token": cookie.value,
        "Content-Type": "application/json",
    }
