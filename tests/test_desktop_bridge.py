from __future__ import annotations

from unittest.mock import Mock

import pytest

from se_kb_app.devtools.desktop import DesktopBridge, render_html
from se_kb_app.devtools.supervisor import Snapshot


@pytest.fixture
def bridge():
    value = DesktopBridge()
    for name in ("web", "api"):
        service = Mock()
        service.snapshot.return_value = Snapshot("stopped", 8000 if name == "web" else 8001,
                                                None, "尚未启动")
        value._services[name] = service
    return value


@pytest.mark.parametrize("action,target,ports,debug", [
    ("exec", "web", {"web":8000, "api":8001}, False),
    ("start", "external", {"web":8000, "api":8001}, False),
    ("start", "all", {"web":8000, "api":8000}, False),
    ("start", "all", {"web":8000, "api":True}, False),
    ("start", "all", {"web":8000.1, "api":8001}, False),
    ("start", "all", {"web":"8000; calc", "api":8001}, False),
    ("start", "all", {"web":8000}, False),
    ("start", "all", None, False),
    ("start", "all", {"web":8000, "api":8001}, "true"),
])
def test_invalid_commands_have_no_process_side_effects(bridge, action, target, ports, debug):
    assert not bridge.command(action,target,ports,debug)["ok"]
    for service in bridge._services.values():
        service.start.assert_not_called()
        service.stop.assert_not_called()


def test_restart_orders_stop_before_start_and_serializes(bridge):
    bridge._operation.acquire()
    assert not bridge.command("stop", "all")["ok"]
    bridge._operation.release()
    assert bridge.command("restart", "web", {"web":8000,"api":8001}, True)["ok"]
    assert [call[0] for call in bridge._services["web"].mock_calls] == [
        "stop", "snapshot", "start", "snapshot",
    ]
    bridge._services["web"].start.assert_called_once_with(8000, True)


def test_failed_stop_prevents_restart_and_window_exit(bridge):
    bridge._services["web"].snapshot.return_value = Snapshot("failed",8000,42,"停止失败")
    bridge._window = Mock()
    assert not bridge.command("restart","web",{"web":8000,"api":8001})["ok"]
    bridge._services["web"].start.assert_not_called()
    assert not bridge.exit()["ok"]
    bridge._window.destroy.assert_not_called()
    assert not bridge._allow_close


def test_native_close_cancel_and_successful_exit(bridge):
    service = bridge._services["web"]
    service.snapshot.return_value = Snapshot("running",8000,42,"HTTP 已响应")
    assert bridge._on_closing() is False
    assert bridge.poll()["close_requested"]
    bridge.cancel_exit()
    assert not bridge.poll()["close_requested"]
    service.stop.assert_not_called()
    service.snapshot.return_value = Snapshot("stopped",8000,None,"已停止")
    bridge._window = Mock()
    assert bridge.exit()["ok"]
    bridge._window.destroy.assert_called_once()
    assert bridge._on_closing() is True
    assert not bridge.command("start","all",{"web":8000,"api":8001})["ok"]


def test_browser_shortcuts_are_fixed_loopback_and_require_running(bridge,monkeypatch):
    opened = Mock(return_value=True)
    monkeypatch.setattr("se_kb_app.devtools.desktop.webbrowser.open",opened)
    assert not bridge.open_service("https://evil.example")["ok"]
    assert not bridge.open_service("api")["ok"]
    opened.assert_not_called()
    bridge._services["api"].snapshot.return_value = Snapshot("running",8123,42,"ok")
    assert bridge.open_service("api")["ok"]
    opened.assert_called_once_with("http://127.0.0.1:8123/apidocs/")


def test_log_polling_is_cursored_bounded_and_redacted():
    bridge = DesktopBridge()
    bridge._services["web"]._secrets = ("secret-test-value",)
    bridge._services["web"].emit("<img src=x onerror=alert(1)> secret-test-value Bearer private-token")
    first = bridge.poll()
    row = first["logs"][0]
    assert "<img" in row["text"]
    assert "secret-test-value" not in row["text"]
    assert "private-token" not in row["text"]
    assert not bridge.poll(first["cursor"])["logs"]
    for index in range(2200):
        bridge._services["api"].emit(f"warning {index}")
        if index % 200 == 0:
            bridge.poll()
    for _ in range(10):
        bridge.poll()
    assert len(bridge._logs) == 2000
    assert len(bridge.poll()["logs"]) <= 300
    assert bridge.clear_logs()["ok"]
    assert not bridge.poll()["logs"]


def test_desktop_document_is_bundled_and_network_disabled():
    html = render_html()
    assert 'href="launcher.css"' not in html
    assert 'src="launcher.js"' not in html
    assert "connect-src 'none'" in html
    assert "textContent = text" in html
    assert "innerHTML" not in html
