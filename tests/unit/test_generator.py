from __future__ import annotations

from salespod.config import Settings
from salespod.infrastructure.seed.generator import SyntheticCrmGenerator


def test_generator_has_exact_counts_and_stable_manifest() -> None:
    settings = Settings()
    first_records, first = SyntheticCrmGenerator(
        seed=settings.seed, as_of=settings.dataset_as_of
    ).generate()
    second_records, second = SyntheticCrmGenerator(
        seed=settings.seed, as_of=settings.dataset_as_of
    ).generate()

    assert len(first_records) == len(second_records) == 2_452
    assert first["content_hash"] == second["content_hash"]
    assert first["counts"] == {
        "companies": 80,
        "leads": 500,
        "deals": 120,
        "email_threads": 1_500,
        "call_transcripts": 60,
        "activities": 60,
        "stage_history": 120,
        "signal_events": 12,
    }


def test_ground_truth_contains_five_missing_economic_buyer_cases() -> None:
    manifest = SyntheticCrmGenerator(as_of=Settings().dataset_as_of).generate()[1]
    cases = manifest["ground_truth_cases"]

    assert len(cases) == 5
    assert all(case["reason"] == "missing_economic_buyer" for case in cases)
    assert all("economic buyer" in " ".join(case["evidence"]["phrases"]) for case in cases)
