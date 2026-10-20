from __future__ import annotations

from typing import Protocol

from salespod.domain.contracts import (
    GetDealResponse,
    LogActivityRequest,
    LogActivityResponse,
    PipelineSnapshotResponse,
    SearchLeadsRequest,
    SearchLeadsResponse,
    UpdateStageRequest,
    UpdateStageResponse,
)


class CrmPort(Protocol):
    def search_leads(self, request: SearchLeadsRequest) -> SearchLeadsResponse: ...

    def get_deal(self, deal_id: str) -> GetDealResponse: ...

    def update_stage(self, request: UpdateStageRequest) -> UpdateStageResponse: ...

    def log_activity(self, request: LogActivityRequest) -> LogActivityResponse: ...

    def get_pipeline_snapshot(self, *, company_id: str | None = None) -> PipelineSnapshotResponse: ...
