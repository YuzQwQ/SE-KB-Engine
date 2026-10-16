from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest


@pytest.mark.contract
def test_every_mcp_tool_matches_golden_name_and_argument_contract(isolated_data_root: Path):
    import server

    golden_path = Path(__file__).parent / "contracts" / "mcp_tool_contracts.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    tools = asyncio.run(server.mcp.list_tools())
    actual = {
        tool.name: sorted(tool.inputSchema.get("properties", {}))
        for tool in tools
    }
    expected = {name: sorted(contract["properties"]) for name, contract in golden.items()}
    assert actual == expected
    assert all(contract["failure"] in {"safe_code", "degraded_or_safe_code"} for contract in golden.values())
