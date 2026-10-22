from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from salespod.application.crm_service import CrmService
from salespod.domain.errors import SalesPodError

from .model_provider import OllamaProvider
from .state import SalesPodState
from .supervisor import Route, route_request
from .tool_facade import CrmToolFacade


def _json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _deterministic_response(tool_name: str | None, observation: dict[str, Any] | None) -> str:
    observation = observation or {}
    if tool_name == "search_leads":
        names = ", ".join(
            f"{item['name']} ({item['title']})" for item in observation.get("items", [])[:5]
        )
        suffix = f" Top matches: {names}." if names else " No matching leads were found."
        return f"Found {observation.get('total_estimate', 0)} matching lead(s).{suffix}"
    if tool_name == "get_pipeline_snapshot":
        amount = observation.get("total_amount_minor", 0) / 100
        weighted = observation.get("weighted_amount_minor", 0) / 100
        return (
            f"Pipeline has {observation.get('total_count', 0)} deal(s) worth ${amount:,.0f}; "
            f"weighted coverage is ${weighted:,.0f}."
        )
    if tool_name == "get_deal":
        deal = observation.get("deal", {})
        return (
            f"{deal.get('name', 'Deal')} is in {deal.get('stage', 'unknown')} at "
            f"${deal.get('amount_minor', 0) / 100:,.0f} with {deal.get('probability', 0):.0%} "
            f"probability (version {deal.get('version', 0)})."
        )
    if tool_name == "update_stage":
        deal = observation.get("deal", {})
        change = observation.get("stage_change", {})
        return (
            f"Moved deal {deal.get('id', '')} from "
            f"{change.get('from_stage', 'unknown')} to {change.get('to_stage', 'unknown')}; "
            f"version is {deal.get('version', 0)}."
        )
    if tool_name == "log_activity":
        activity = observation.get("activity", {})
        return f"Logged {activity.get('activity_type', 'note')} activity {activity.get('id', '')}."
    return f"Completed {tool_name or 'request'}."


class DeterministicSalesPodGraph:
    """Fallback graph with the same invoke contract as a compiled LangGraph."""

    def __init__(self, nodes: list[Callable[[SalesPodState], SalesPodState]]) -> None:
        self.nodes = nodes

    def invoke(self, state: SalesPodState | dict[str, Any]) -> SalesPodState:
        result: SalesPodState = dict(state)  # type: ignore[assignment]
        for node in self.nodes:
            result.update(node(result))
        return result


def build_graph(
    service: CrmService,
    *,
    provider: OllamaProvider | None = None,
    use_ollama: bool = False,
    prefer_langgraph: bool = True,
):
    """Build a checkpoint-compatible LangGraph when installed, else a local fallback."""
    facade = CrmToolFacade(service)

    def normalize(state: SalesPodState) -> SalesPodState:
        request = str(state.get("request", "")).strip()
        if not request:
            return {"errors": ["request cannot be empty"]}
        return {
            "request": request,
            "actor": state.get("actor", "manager"),
            "trace_id": state.get("trace_id", str(uuid4())),
            "observations": state.get("observations", []),
            "errors": state.get("errors", []),
        }

    def supervise(state: SalesPodState) -> SalesPodState:
        if state.get("errors"):
            return {}
        route: Route = route_request(state["request"], actor=state.get("actor", "manager"))
        result: SalesPodState = {"intent": route.intent, "tool_args": route.tool_args}
        if route.tool_name:
            result["tool_name"] = route.tool_name
        if route.error:
            result["errors"] = [route.error]
        return result

    def execute(state: SalesPodState) -> SalesPodState:
        if state.get("errors") or not state.get("tool_name"):
            return {}
        try:
            observation = facade.execute(state["tool_name"], state.get("tool_args", {}))
            serialized = _json(observation)
            return {
                "observations": [{"tool": state["tool_name"], "result": serialized}],
                "observation": serialized,
            }
        except SalesPodError as exc:
            return {"errors": [f"{exc.code}: {exc}"]}
        except (KeyError, ValueError, TypeError) as exc:
            return {"errors": [f"VALIDATION_ERROR: {exc}"]}

    def synthesize(state: SalesPodState) -> SalesPodState:
        errors = state.get("errors", [])
        if errors:
            return {"response": f"I could not complete that request: {errors[0]}"}
        observations = state.get("observations", [])
        observation = state.get("observation")
        if use_ollama and provider is not None and observation is not None:
            prompt = (
                "Respond to this sales manager request in two concise sentences. "
                "Use only the structured CRM observation; do not invent facts.\n"
                f"Request: {state.get('request')}\nObservation: {json.dumps(observations)}"
            )
            generated = provider.chat(prompt)
            if generated:
                return {"response": generated}
        return {"response": _deterministic_response(state.get("tool_name"), observation)}

    nodes = [normalize, supervise, execute, synthesize]
    if not prefer_langgraph:
        return DeterministicSalesPodGraph(nodes)
    try:
        from langgraph.graph import END, START, StateGraph

        workflow = StateGraph(SalesPodState)
        workflow.add_node("normalize_request", normalize)
        workflow.add_node("supervisor", supervise)
        workflow.add_node("execute_tool", execute)
        workflow.add_node("synthesize_response", synthesize)
        workflow.add_edge(START, "normalize_request")
        workflow.add_edge("normalize_request", "supervisor")
        workflow.add_edge("supervisor", "execute_tool")
        workflow.add_edge("execute_tool", "synthesize_response")
        workflow.add_edge("synthesize_response", END)
        return workflow.compile()
    except ImportError:
        return DeterministicSalesPodGraph(nodes)
