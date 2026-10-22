from __future__ import annotations

from typing import Any, TypedDict


class SalesPodState(TypedDict, total=False):
    request: str
    actor: str
    trace_id: str
    intent: str
    tool_name: str
    tool_args: dict[str, Any]
    observations: list[dict[str, Any]]
    observation: dict[str, Any]
    response: str
    errors: list[str]
