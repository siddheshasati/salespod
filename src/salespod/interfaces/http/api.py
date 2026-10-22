from __future__ import annotations

from typing import Annotated, Any, Protocol
from uuid import UUID

from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from salespod.agents.graph import build_graph
from salespod.application.crm_service import CrmService
from salespod.config import Settings
from salespod.domain.contracts import (
    GetDealResponse,
    SearchLeadsRequest,
    SearchLeadsResponse,
    UpdateStageRequest,
    UpdateStageResponse,
)
from salespod.domain.errors import ConflictError, NotFoundError, SalesPodError, ValidationError
from salespod.infrastructure.db.session import create_schema, create_session_factory

from .approvals import ApprovalRepository
from .dashboard import DashboardRepository
from .schemas import (
    AgentAskRequest,
    AgentAskResponse,
    ApprovalDecisionRequest,
    ApprovalRecord,
    DashboardOverview,
    DashboardPipelineTotals,
    ErrorResponse,
    HealthResponse,
    StageChangeRequest,
)


class SalesPodGraph(Protocol):
    def invoke(self, state: dict[str, Any]) -> dict[str, Any]: ...


def _status_code(error: SalesPodError) -> int:
    if isinstance(error, NotFoundError):
        return 404
    if isinstance(error, ConflictError):
        return 409
    if isinstance(error, ValidationError):
        return 422
    return 400


def _service(request: Request) -> CrmService:
    return request.app.state.crm_service


def _session_factory(request: Request) -> sessionmaker[Session]:
    return request.app.state.session_factory


def _approvals(request: Request) -> ApprovalRepository:
    return request.app.state.approvals


def _dashboard(request: Request) -> DashboardRepository:
    return request.app.state.dashboard


def _graph(request: Request) -> SalesPodGraph:
    return request.app.state.graph


def create_app(
    service: CrmService | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
    graph: SalesPodGraph | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Create an isolated API app, with injectable services for tests and tools."""
    if service is None:
        if session_factory is None:
            settings = settings or Settings.from_env()
            settings.ensure_database_parent()
            create_schema(settings.database_url)
            session_factory = create_session_factory(settings.database_url)
        service = CrmService(session_factory)
    elif session_factory is None:
        session_factory = service.session_factory

    if session_factory is None:  # pragma: no cover - defensive guard for type checkers
        raise RuntimeError("a SQLAlchemy session factory is required")
    graph = graph or build_graph(service, prefer_langgraph=False)

    app = FastAPI(title="Sales Pod API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.crm_service = service
    app.state.session_factory = session_factory
    app.state.approvals = ApprovalRepository(session_factory)
    app.state.dashboard = DashboardRepository(session_factory)
    app.state.graph = graph

    @app.exception_handler(SalesPodError)
    async def handle_salespod_error(_request: Request, exc: SalesPodError) -> JSONResponse:
        body = ErrorResponse(code=exc.code, message=str(exc))
        return JSONResponse(status_code=_status_code(exc), content=body.model_dump(mode="json"))

    @app.get("/api/health", response_model=HealthResponse, tags=["system"])
    def health(
        session_factory: Annotated[sessionmaker[Session], Depends(_session_factory)],
    ) -> HealthResponse:
        with session_factory() as session:
            session.execute(select(1))
        return HealthResponse(status="ok", database="ok")

    @app.get("/api/dashboard/overview", response_model=DashboardOverview, tags=["dashboard"])
    def dashboard_overview(
        service: Annotated[CrmService, Depends(_service)],
        dashboard: Annotated[DashboardRepository, Depends(_dashboard)],
        approvals: Annotated[ApprovalRepository, Depends(_approvals)],
    ) -> DashboardOverview:
        snapshot = service.get_pipeline_snapshot()
        return DashboardOverview(
            generated_at=snapshot.generated_at,
            pipeline_totals=DashboardPipelineTotals(
                currency=snapshot.currency,
                total_count=snapshot.total_count,
                total_amount_minor=snapshot.total_amount_minor,
                weighted_amount_minor=snapshot.weighted_amount_minor,
            ),
            stage_summaries=snapshot.stages,
            risk_counts=approvals.risk_counts(),
            recent_activities=dashboard.recent_activities(),
        )

    @app.get("/api/leads", tags=["crm"])
    def leads(
        service: Annotated[CrmService, Depends(_service)],
        query: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
    ) -> SearchLeadsResponse:
        return service.search_leads(SearchLeadsRequest(query=query, limit=limit))

    @app.get("/api/deals/{deal_id}", tags=["crm"])
    def deal(
        deal_id: UUID,
        service: Annotated[CrmService, Depends(_service)],
    ) -> GetDealResponse:
        return service.get_deal(deal_id)

    @app.get("/api/approvals", response_model=list[ApprovalRecord], tags=["approvals"])
    def approvals(
        approval_repository: Annotated[ApprovalRepository, Depends(_approvals)],
    ) -> list[ApprovalRecord]:
        return approval_repository.list()

    @app.post(
        "/api/approvals/{approval_id}/decision",
        response_model=ApprovalRecord,
        tags=["approvals"],
    )
    def approval_decision(
        approval_repository: Annotated[ApprovalRepository, Depends(_approvals)],
        approval_id: Annotated[str, Path(min_length=1)],
        decision: ApprovalDecisionRequest,
    ) -> ApprovalRecord:
        return approval_repository.decide(approval_id, decision)

    @app.post("/api/agent/ask", response_model=AgentAskResponse, tags=["agent"])
    def agent_ask(
        request: AgentAskRequest,
        graph: Annotated[SalesPodGraph, Depends(_graph)],
    ) -> AgentAskResponse:
        result = graph.invoke({"request": request.request, "actor": request.actor})
        return AgentAskResponse(
            request=str(result.get("request", request.request)),
            actor=str(result.get("actor", request.actor)),
            trace_id=str(result.get("trace_id", "")),
            intent=result.get("intent"),
            tool_name=result.get("tool_name"),
            response=str(result.get("response", "")),
            observations=result.get("observations", []),
            errors=result.get("errors", []),
        )

    @app.post("/api/deals/{deal_id}/stage", tags=["crm"])
    def update_deal_stage(
        stage: StageChangeRequest,
        deal_id: UUID,
        service: Annotated[CrmService, Depends(_service)],
    ) -> UpdateStageResponse:
        request = UpdateStageRequest(deal_id=deal_id, **stage.model_dump())
        return service.update_stage(request)

    return app


app = create_app()
