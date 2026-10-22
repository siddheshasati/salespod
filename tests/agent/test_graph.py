from __future__ import annotations

from salespod.agents.graph import build_graph
from salespod.agents.supervisor import route_request
from salespod.infrastructure.seed.generator import stable_id


def test_supervisor_requires_explicit_mutation_version() -> None:
    deal_id = stable_id("deal", 0)
    route = route_request(f"Update stage {deal_id} to closed_lost")
    assert route.tool_name is None
    assert "expected version" in (route.error or "")


def test_graph_answers_pipeline_without_ollama(seeded_service) -> None:
    graph = build_graph(seeded_service, prefer_langgraph=False)
    result = graph.invoke({"request": "Show the current pipeline snapshot"})
    assert result["intent"] == "pipeline_snapshot"
    assert "Pipeline has 120 deal(s)" in result["response"]
    assert not result.get("errors")


def test_graph_executes_only_explicit_stage_change(seeded_service) -> None:
    deal_id = stable_id("deal", 0)
    graph = build_graph(seeded_service, prefer_langgraph=False)
    result = graph.invoke(
        {
            "request": f"Update stage {deal_id} to closed_lost version 1",
            "actor": "rep-1",
        }
    )
    assert result["intent"] == "update_stage"
    assert "closed_lost" in result["response"]
