"""Opt-in native WebView2 integration smoke: real bridge, DOM and local workers."""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from se_kb_app.devtools.desktop import DesktopBridge, render_html


def main() -> None:
    import webview

    with tempfile.TemporaryDirectory(prefix="se-kb-webview-") as directory:
        os.environ.update({"SE_KB_PROJECT_ROOT": directory, "SE_KB_SKIP_DOTENV":"1",
                           "SKIP_SERVICE_INITIALIZATION":"1"})
        bridge = DesktopBridge()
        window = webview.create_window("SE-KB · WebView smoke", html=render_html(), js_api=bridge,
                                       width=1240,height=850)
        if window is None:
            raise RuntimeError("no window")
        bridge._window = window
        window.events.closing += bridge._on_closing
        failures = []

        def wait_js(expression):
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                if window.evaluate_js(expression):
                    return
                time.sleep(0.1)
            raise AssertionError(expression + " :: " + str(bridge.poll()))

        def smoke():
            try:
                window.events.loaded.wait(15)
                wait_js("document.getElementById('connectionText').textContent === '桌面已连接'")
                ports = []
                for _ in range(2):
                    with socket.socket() as sock:
                        sock.bind(("127.0.0.1",0))
                        ports.append(sock.getsockname()[1])
                if ports[0] == ports[1]:
                    raise AssertionError("retry smoke with distinct available ports")
                window.evaluate_js(f"document.getElementById('webPort').value='{ports[0]}';"
                                   f"document.getElementById('apiPort').value='{ports[1]}';"
                                   "document.querySelector('[data-action=start][data-target=all]').click()")
                wait_js("document.querySelectorAll('.service-card[data-status=running]').length === 2")
                old_pid = bridge._services["web"].snapshot().pid
                window.evaluate_js("document.getElementById('debugMode').click();"
                                   "document.querySelector('[data-action=restart][data-target=web]').click()")
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    state = bridge._services["web"].snapshot()
                    if state.status == "running" and state.pid != old_pid:
                        break
                    time.sleep(0.1)
                else:
                    raise AssertionError("restart did not replace PID")
                bridge._services["web"].emit("<img src=x onerror=alert(1)> warning literal log")
                wait_js("document.getElementById('logOutput').textContent.includes('warning literal log')")
                assert window.evaluate_js("document.querySelectorAll('#logOutput img').length === 0")
                window.destroy()
                wait_js("document.getElementById('exitDialog').open")
                window.evaluate_js("document.getElementById('cancelExit').click()")
                wait_js("!document.getElementById('exitDialog').open")
                assert all(s.snapshot().pid for s in bridge._services.values())
                window.evaluate_js("document.getElementById('exitButton').click();"
                                   "document.getElementById('confirmExit').click()")
            except Exception as error:
                failures.append(str(error))
                bridge.exit()

        try:
            webview.start(smoke, private_mode=True)
        finally:
            bridge._cleanup()
        if failures:
            raise AssertionError("\n".join(failures))
        assert not any(s.snapshot().pid for s in bridge._services.values())
        print("Native webview: bridge, start-all, debug restart, safe logs, close cancellation and exit: PASS")


if __name__ == "__main__":
    main()
