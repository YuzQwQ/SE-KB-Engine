from __future__ import annotations

import os
import random
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import httpx


class ProxyPool:
    """简单的代理池：从文件或环境变量加载代理，提供轮换与健康检查。

    支持协议：http、https、socks5（若安装 httpx_socks）。
    文件格式：每行一个代理，例如：
      - http://user:pass@host:port
      - http://host:port
      - socks5://host:port
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent  # export/crawler_core
        self.enabled = os.getenv("PROXY_POOL_ENABLED", "0").strip().lower() not in ("0", "false")
        self.proxies: List[str] = []
        self._cursor = 0
        self._load()

    def _load(self) -> None:
        # 单个代理直接用环境变量
        single = os.getenv("PROXY_URL", "").strip()
        if single:
            self.proxies = [single]
            return

        # 从文件加载列表
        file_env = os.getenv("PROXY_POOL_FILE", "config/proxies.txt").strip()
        path = Path(file_env)
        if not path.is_absolute():
            path = (self.base_dir / file_env).resolve()
        if path.exists():
            lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
            self.proxies = lines

    def is_enabled(self) -> bool:
        # 只要存在代理列表（来自 PROXY_URL 或文件），即视为可用
        return len(self.proxies) > 0

    def get_next(self) -> Optional[str]:
        if not self.is_enabled():
            return None
        proxy = self.proxies[self._cursor % len(self.proxies)]
        self._cursor = (self._cursor + 1) % max(1, len(self.proxies))
        return proxy

    def mark_failure(self, proxy: Optional[str]) -> None:
        # 简易策略：失败不移除，保持轮换；可扩展为熔断与恢复
        pass

    def create_httpx_client(self, proxy: Optional[str], headers: Dict[str, str], timeout: int = 15) -> httpx.Client:
        if proxy and proxy.startswith("socks"):
            # 可选：使用 httpx_socks 的同步 transport
            try:
                from httpx_socks import SyncProxyTransport  # type: ignore
                transport = SyncProxyTransport.from_url(proxy)
                return httpx.Client(transport=transport, headers=headers, timeout=timeout)
            except Exception:
                # 回退为无代理
                return httpx.Client(headers=headers, timeout=timeout)
        elif proxy:
            proxies = {"http": proxy, "https": proxy}
            return httpx.Client(proxies=proxies, headers=headers, timeout=timeout)
        else:
            return httpx.Client(headers=headers, timeout=timeout)

    def playwright_proxy_arg(self, proxy: Optional[str]) -> Optional[Dict[str, str]]:
        if not proxy:
            return None
        try:
            # Playwright 仅需 server（可包含协议与认证）
            return {"server": proxy}
        except Exception:
            return None