from __future__ import annotations

from salespod.application.signal_stream import SignalStreamService
from salespod.domain.enums import SignalEventType


def test_simulate_event_for_all_five_types(seeded_service) -> None:
    types = ["funding_round", "new_cto", "layoffs", "tech_stack", "leadership_change"]
    with seeded_service.session_factory() as session:
        service = SignalStreamService(session)
        for t in types:
            sig = service.simulate_event(event_type=t)
            assert sig.id is not None
            assert sig.headline is not None
            assert sig.summary is not None
            assert sig.relevance_score >= 85
            assert sig.payload_json.get("simulated") is True


def test_seed_stream_cohort(seeded_service) -> None:
    with seeded_service.session_factory() as session:
        service = SignalStreamService(session)
        cohort = service.seed_stream_cohort()
        assert len(cohort) == 5
        event_types = {e.event_type for e in cohort}
        assert SignalEventType.NEW_CTO.value in event_types
        assert SignalEventType.FUNDING_ROUND.value in event_types
        assert SignalEventType.LAYOFFS.value in event_types
