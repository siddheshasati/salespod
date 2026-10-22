from __future__ import annotations

from pathlib import Path

import pytest

from salespod.application.crm_service import CrmService
from salespod.config import Settings
from salespod.infrastructure.db.session import create_session_factory
from salespod.infrastructure.seed.generator import seed_database


@pytest.fixture
def seeded_service(tmp_path: Path) -> CrmService:
    database_url = f"sqlite:///{tmp_path / 'salespod.db'}"
    seed_database(
        database_url,
        seed=424242,
        as_of=Settings().dataset_as_of,
        reset=True,
    )
    return CrmService(create_session_factory(database_url))
