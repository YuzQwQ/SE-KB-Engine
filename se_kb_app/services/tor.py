from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from time import monotonic, sleep
from typing import Any

from se_kb_app.errors import ErrorKind, wrap_error


ProcessFactory = Callable[..., Any]


class TorController:
    """Explicitly managed Tor process; construction never starts a process."""

    def __init__(
        self,
        *,
        enabled: bool,
        executable: str = "tor",
        socks_port: int = 9050,
        control_port: int = 9051,
        data_dir: Path | None = None,
        process_factory: ProcessFactory = subprocess.Popen,
        readiness_probe: Callable[[], bool] | None = None,
        startup_timeout_seconds: float = 10.0,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.enabled = enabled
        self.executable = executable
        self.socks_port = socks_port
        self.control_port = control_port
        self.data_dir = (data_dir or Path(".cache/tor")).resolve()
        self.process_factory = process_factory
        self.readiness_probe = readiness_probe or (lambda: self.running)
        self.startup_timeout_seconds = startup_timeout_seconds
        self.clock = clock
        self.sleeper = sleeper
        self.process: Any | None = None

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @property
    def is_running(self) -> bool:
        return self.running

    @property
    def proxy_url(self) -> str | None:
        return f"socks5://127.0.0.1:{self.socks_port}" if self.running else None

    def start(self) -> bool:
        if not self.enabled:
            return False
        if self.running:
            return True
        self.data_dir.mkdir(parents=True, exist_ok=True)
        command = [
            self.executable,
            "--SocksPort",
            str(self.socks_port),
            "--ControlPort",
            str(self.control_port),
            "--DataDirectory",
            str(self.data_dir),
        ]
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.process = self.process_factory(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise wrap_error(
                ErrorKind.NETWORK,
                "tor_start_failed",
                "Tor could not be started.",
                retryable=False,
                cause=error,
            ) from error
        started = self.clock()
        while self.running and self.clock() - started < self.startup_timeout_seconds:
            if self.readiness_probe():
                return True
            self.sleeper(0.05)
        self.close()
        timeout = TimeoutError("Tor readiness deadline exceeded")
        raise wrap_error(
            ErrorKind.NETWORK,
            "tor_start_timeout",
            "Tor did not become ready before its startup deadline.",
            retryable=False,
            cause=timeout,
        ) from timeout

    def new_identity(self) -> bool:
        self.close()
        return self.start()

    def start_tor(self) -> bool:
        return self.start()

    def get_proxy_config(self) -> str | None:
        return self.proxy_url

    def cleanup(self) -> None:
        self.close()

    def close(self) -> None:
        if self.process is None:
            return
        process, self.process = self.process, None
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
