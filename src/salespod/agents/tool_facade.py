from __future__ import annotations

from typing import Any

from salespod.application.crm_service import CrmService
from salespod.domain.contracts import (
    LogActivityRequest,
    SearchLeadsRequest,
    UpdateStageRequest,
)


class CrmToolFacade:
    """Typed in-process facade; a remote MCP client can implement the same shape."""

    def __init__(self, service: CrmService) -> None:
        self.service = service

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "search_leads":
            return self.service.search_leads(SearchLeadsRequest.model_validate(arguments))
        if tool_name == "get_deal":
            return self.service.get_deal(arguments["deal_id"])
        if tool_name == "update_stage":
            return self.service.update_stage(UpdateStageRequest.model_validate(arguments))
        if tool_name == "log_activity":
            return self.service.log_activity(LogActivityRequest.model_validate(arguments))
        if tool_name == "get_pipeline_snapshot":
            return self.service.get_pipeline_snapshot(**arguments)
        if tool_name == "analyze_q4_risk":
            return self.service.analyze_q4_risk()
        raise ValueError(f"unsupported CRM tool: {tool_name}")
