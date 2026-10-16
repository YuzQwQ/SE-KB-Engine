"""Opt-in Tk + real loopback service smoke check; no models or external network."""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from se_kb_app.devtools.window import LauncherWindow


def available_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="se-kb-launcher-") as directory:
        os.environ.update({"SE_KB_PROJECT_ROOT": directory, "SE_KB_SKIP_DOTENV": "1",
                           "SKIP_SERVICE_INITIALIZATION": "1"})
        root = tk.Tk()
        root.withdraw()
        window = LauncherWindow(root)

        def wait_until(predicate) -> None:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                root.update()
                if predicate():
                    return
                time.sleep(0.05)
            raise AssertionError([service.snapshot() for service in window.services.values()])

        try:
            ports = set()
            for variable in window.ports.values():
                port = available_port()
                while port in ports:
                    port = available_port()
                ports.add(port)
                variable.set(str(port))
            window.debug.set(True)
            window.all_buttons[0].invoke()
            wait_until(lambda: all(s.snapshot().status == "running"
                                   for s in window.services.values()) and not window.busy.is_set())
            with patch("se_kb_app.devtools.window.messagebox.askokcancel", return_value=False):
                window.close()
            assert not window.closing
            assert all(s.snapshot().status == "running" for s in window.services.values())
            window.service_buttons["web"][1].invoke()
            wait_until(lambda: not window.busy.is_set()
                       and window.services["web"].snapshot().status == "running")
            window.all_buttons[2].invoke()
            wait_until(lambda: not window.busy.is_set()
                       and all(s.snapshot().status == "stopped" for s in window.services.values()))
            assert "PID=" in window.log_views["all"].get("1.0", "end")
            window.clear_logs()
            assert not window.log_views["all"].get("1.0", "end").strip()
            print("Tk window, start-all, debug restart, close cancellation, logs and stop-all: PASS")
        finally:
            for service in window.services.values():
                service.stop()
            root.after_cancel(window.timer)
            root.destroy()


if __name__ == "__main__":
    main()
