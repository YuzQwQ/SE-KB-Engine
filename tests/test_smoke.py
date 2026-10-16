"""入口 smoke 测试（BOOT-010/014/018）。

验证三个正式入口 + MCP 客户端可以在离线环境完成导入，
且 MCP 服务器能注册并列出全部工具，不触发真实网络请求。

实现方式：每个入口在独立子进程中导入，避免模块级初始化
（ChromaDB、日志配置）污染 pytest 进程；注入占位 API Key，
使测试在无真实密钥的干净机器上同样可运行（TEST-020）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 占位密钥：只求构造函数不抛异常，不发起任何真实请求
PLACEHOLDER_ENV = {
    "OPENAI_API_KEY": "sk-test-placeholder",
    "BASE_URL": "https://example.invalid/v1",
}


def _run_import(code: str, timeout: int = 120) -> subprocess.CompletedProcess:
    guard_path = PROJECT_ROOT / "tests" / "offline_guard"
    env = {
        **os.environ,
        **PLACEHOLDER_ENV,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SE_KB_SKIP_DOTENV": "1",
        "PYTHONPATH": os.pathsep.join((str(guard_path), str(PROJECT_ROOT))),
    }
    with tempfile.TemporaryDirectory(prefix="se-kb-smoke-") as temp_dir:
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=temp_dir,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )


@pytest.mark.integration
def test_import_server_module():
    """server.py（MCP 服务器单体）可离线导入，导入期不启动服务。"""
    proc = _run_import("import server; print('OK', bool(server.mcp))")
    assert proc.returncode == 0, f"stderr: {proc.stderr[-2000:]}"
    assert "OK True" in proc.stdout


@pytest.mark.integration
def test_import_web_app():
    """web.app（Flask 控制台）可离线导入。"""
    proc = _run_import("import web.app as wa; print('OK', wa.app.name)")
    assert proc.returncode == 0, f"stderr: {proc.stderr[-2000:]}"
    assert "OK" in proc.stdout


@pytest.mark.integration
def test_import_api_app():
    """api.app（检索 API）可离线导入。"""
    proc = _run_import("import api.app; print('OK')")
    assert proc.returncode == 0, f"stderr: {proc.stderr[-2000:]}"
    assert "OK" in proc.stdout


@pytest.mark.integration
def test_import_mcp_client():
    """client.py（MCP 客户端 CLI）可离线导入。"""
    proc = _run_import("import client; print('OK')")
    assert proc.returncode == 0, f"stderr: {proc.stderr[-2000:]}"
    assert "OK" in proc.stdout


@pytest.mark.integration
def test_mcp_list_tools_offline():
    """MCP 服务器能列出全部已注册工具（BOOT-014），且过程不访问网络。"""
    code = (
        "import asyncio, json\n"
        "import server\n"
        "tools = asyncio.run(server.mcp.list_tools())\n"
        "print(json.dumps([t.name for t in tools]))\n"
    )
    proc = _run_import(code)
    assert proc.returncode == 0, f"stderr: {proc.stderr[-2000:]}"
    names = json.loads(proc.stdout.strip().splitlines()[-1])
    # 回归守卫：2026-09 修复语法损坏后恢复的 23 个工具（UNIT-023）
    assert len(names) >= 20, f"工具数量异常: {len(names)}"
    expected_subset = {
        "fetch_raw_data", "parse_search_results", "scrape_webpage",
        "crawl_webpage_direct", "search_knowledge", "validate_tor_config",
    }
    missing = expected_subset - set(names)
    assert not missing, f"关键工具缺失: {missing}"
