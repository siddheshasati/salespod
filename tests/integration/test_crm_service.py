from __future__ import annotations

from uuid import UUID

import pytest

from salespod.domain.contracts import LogActivityRequest, SearchLeadsRequest, UpdateStageRequest
from salespod.domain.enums import ActivityType, DealStage
from salespod.domain.errors import ConflictError, ValidationError
from salespod.infrastructure.seed.generator import stable_id


def test_search_leads_and_pipeline_snapshot(seeded_service) -> None:
    result = seeded_service.search_leads(SearchLeadsRequest(query="example.com", limit=7))
    snapshot = seeded_service.get_pipeline_snapshot()

    assert result.total_estimate == 500
    assert len(result.items) == 7
    assert result.next_cursor
    assert snapshot.total_count == 120
    assert snapshot.total_amount_minor > 0
    assert snapshot.weighted_amount_minor > 0


def test_deal_update_uses_optimistic_concurrency_and_idempotency(seeded_service) -> None:
    deal_id = UUID(stable_id("deal", 0))
    request = UpdateStageRequest(
        deal_id=deal_id,
        new_stage=DealStage.CLOSED_LOST,
        reason="Forecast review found no confirmed economic buyer.",
        actor="test-rep",
        expected_version=1,
        idempotency_key="test-stage-update-0",
    )

    first = seeded_service.update_stage(request)
    replay = seeded_service.update_stage(request)

    assert first.deal.version == replay.deal.version == 2
    assert first.stage_change.id == replay.stage_change.id
    with pytest.raises(ConflictError):
        seeded_service.update_stage(
            request.model_copy(update={"idempotency_key": "different", "expected_version": 1})
        )


def test_activity_requires_entity_and_replays_idempotently(seeded_service) -> None:
    request = LogActivityRequest(
        activity_type=ActivityType.NOTE,
        body="Stakeholder mapping completed.",
        actor="test-rep",
        deal_id=UUID(stable_id("deal", 1)),
        idempotency_key="note-1",
    )
    first = seeded_service.log_activity(request)
    replay = seeded_service.log_activity(request)
    assert first.activity.id == replay.activity.id

    with pytest.raises(ValidationError):
        seeded_service.log_activity(
            LogActivityRequest(activity_type=ActivityType.NOTE, body="orphan", actor="test-rep")
        )
