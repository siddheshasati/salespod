from __future__ import annotations

import argparse
from datetime import datetime
from typing import Any
from uuid import UUID

from salespod.application.crm_service import CrmService
from salespod.application.signal_service import SignalService
from salespod.config import Settings
from salespod.domain.contracts import (
    ListSignalsRequest,
    LogActivityRequest,
    SearchLeadsRequest,
    UpdateStageRequest,
)
from salespod.domain.enums import ActivityType, DealStage, LeadStatus, SignalEventType, SignalStatus
from salespod.domain.errors import SalesPodError
from salespod.infrastructure.db.session import create_session_factory

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only in an uninstalled checkout
    FastMCP = None  # type: ignore[assignment,misc]


TOOL_NAMES = (
    "search_leads",
    "get_deal",
    "update_stage",
    "log_activity",
    "get_pipeline_snapshot",
    "list_signal_events",
    "get_signal_event",
    "acknowledge_signal",
)


def _error(exc: SalesPodError) -> RuntimeError:
    return RuntimeError(f"{exc.code}: {exc}")


def create_server(service: CrmService | None = None):
    """Create an isolated FastMCP server around an injected CRM service."""
    if FastMCP is None:
        raise RuntimeError("FastMCP is not installed; run pip install -e '.[dev,agents]'")
    if service is None:
        settings = Settings.from_env()
        settings.ensure_database_parent()
        service = CrmService(create_session_factory(settings.database_url))
    signal_service = SignalService(service.session_factory)
    mcp = FastMCP("salespod-crm")

    @mcp.tool(name="search_leads")
    def search_leads(
        query: str | None = None,
        company_id: UUID | None = None,
        status: LeadStatus | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        try:
            result = service.search_leads(
                SearchLeadsRequest(
                    query=query, company_id=company_id, status=status, limit=limit, cursor=cursor
                )
            )
            return result.model_dump(mode="json")
        except SalesPodError as exc:
            raise _error(exc) from exc

    @mcp.tool(name="get_deal")
    def get_deal(deal_id: UUID) -> dict[str, Any]:
        try:
            return service.get_deal(deal_id).model_dump(mode="json")
        except SalesPodError as exc:
            raise _error(exc) from exc

    @mcp.tool(name="update_stage")
    def update_stage(
        deal_id: UUID,
        new_stage: DealStage,
        reason: str,
        actor: str,
        expected_version: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        try:
            result = service.update_stage(
                UpdateStageRequest(
                    deal_id=deal_id,
                    new_stage=new_stage,
                    reason=reason,
                    actor=actor,
                    expected_version=expected_version,
                    idempotency_key=idempotency_key,
                )
            )
            return result.model_dump(mode="json")
        except SalesPodError as exc:
            raise _error(exc) from exc

    @mcp.tool(name="log_activity")
    def log_activity(
        activity_type: ActivityType,
        body: str,
        actor: str,
        occurred_at: datetime | None = None,
        company_id: UUID | None = None,
        lead_id: UUID | None = None,
        deal_id: UUID | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            result = service.log_activity(
                LogActivityRequest(
                    activity_type=activity_type,
                    body=body,
                    actor=actor,
                    occurred_at=occurred_at,
                    company_id=company_id,
                    lead_id=lead_id,
                    deal_id=deal_id,
                    idempotency_key=idempotency_key,
                    metadata=metadata or {},
                )
            )
            return result.model_dump(mode="json")
        except SalesPodError as exc:
            raise _error(exc) from exc

    @mcp.tool(name="get_pipeline_snapshot")
    def get_pipeline_snapshot(
        as_of: datetime | None = None,
        company_id: UUID | None = None,
        owner: str | None = None,
    ) -> dict[str, Any]:
        try:
            return service.get_pipeline_snapshot(
                as_of=as_of, company_id=company_id, owner=owner
            ).model_dump(mode="json")
        except SalesPodError as exc:
            raise _error(exc) from exc

    @mcp.tool(name="list_signal_events")
    def list_signal_events(
        company_id: UUID | None = None,
        event_type: SignalEventType | None = None,
        status: SignalStatus | None = None,
        query: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        try:
            result = signal_service.list_events(
                ListSignalsRequest(
                    company_id=company_id,
                    event_type=event_type,
                    status=status,
                    query=query,
                    limit=limit,
                )
            )
            return [item.model_dump(mode="json") for item in result]
        except SalesPodError as exc:
            raise _error(exc) from exc

    @mcp.tool(name="get_signal_event")
    def get_signal_event(signal_id: UUID) -> dict[str, Any]:
        try:
            return signal_service.get_event(signal_id).model_dump(mode="json")
        except SalesPodError as exc:
            raise _error(exc) from exc

    @mcp.tool(name="acknowledge_signal")
    def acknowledge_signal(
        signal_id: UUID,
        actor: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        try:
            return signal_service.acknowledge(
                signal_id,
                actor=actor,
                note=note,
            ).model_dump(mode="json")
        except SalesPodError as exc:
            raise _error(exc) from exc

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Sales Pod CRM MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    args = parser.parse_args()
    server = create_server()
    server.run(transport=args.transport)
