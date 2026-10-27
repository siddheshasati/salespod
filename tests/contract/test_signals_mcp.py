from __future__ import annotations

import asyncio

from salespod.interfaces.mcp.signals_server import (
    SIGNALS_TOOL_NAMES,
    SignalsIntelligenceSource,
    create_signals_server,
)


def test_signals_mcp_server_contract(seeded_service) -> None:
    server = create_signals_server(seeded_service.session_factory)
    assert server.name == "signals-mcp"

    tools = asyncio.run(server.get_tools())
    assert set(SIGNALS_TOOL_NAMES).issubset(set(tools))
    assert tuple(tools) == SIGNALS_TOOL_NAMES


def test_signals_intelligence_tools(seeded_service) -> None:
    source = SignalsIntelligenceSource(seeded_service.session_factory)

    # 1. get_company_news
    news = source.get_company_news(query="expansion")
    assert isinstance(news, list)
    assert len(news) > 0
    assert "title" in news[0]
    assert "summary" in news[0]

    # 2. get_funding_events
    funding = source.get_funding_events()
    assert isinstance(funding, list)
    assert len(funding) >= 2
    assert funding[0]["round"] == "Series B"
    assert funding[0]["amount_usd"] == 42_000_000

    # 3. get_tech_stack
    tech = source.get_tech_stack(domain="example.com")
    assert isinstance(tech, dict)
    assert "technologies" in tech
    assert "crm" in tech["technologies"]
    assert tech["technologies"]["crm"]["name"] == "Salesforce Sales Cloud"
