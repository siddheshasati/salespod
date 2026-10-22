from __future__ import annotations

import asyncio

from salespod.interfaces.mcp.server import TOOL_NAMES, create_server


def test_fastmcp_exposes_exact_crm_tools(seeded_service) -> None:
    server = create_server(seeded_service)
    tools = asyncio.run(server.get_tools())
    assert tuple(tools) == TOOL_NAMES
    assert set(tools) == set(TOOL_NAMES)
