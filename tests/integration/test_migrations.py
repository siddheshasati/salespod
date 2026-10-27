from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from salespod.infrastructure.db.session import migrate_database

ROOT = Path(__file__).resolve().parents[2]
HEAD = "0004_signal_events"


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _revision(database_url: str) -> str:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


def test_migrate_database_creates_latest_schema(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'fresh.db'}"

    migrate_database(database_url)

    inspector = inspect(create_engine(database_url))
    assert _revision(database_url) == HEAD
    assert {"companies", "deals", "approval_requests", "audit_events"}.issubset(
        inspector.get_table_names()
    )
    assert "deal_id" in {column["name"] for column in inspector.get_columns("call_transcripts")}


def test_transcript_constraint_migration_is_reversible_on_sqlite(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'reversible.db'}"
    migrate_database(database_url)

    command.downgrade(_alembic_config(database_url), "0002_control_plane")
    downgraded = inspect(create_engine(database_url))
    assert "ix_call_transcripts_deal_id" not in {
        index["name"] for index in downgraded.get_indexes("call_transcripts")
    }

    command.upgrade(_alembic_config(database_url), "head")
    assert _revision(database_url) == HEAD


def test_migrate_database_upgrades_an_unversioned_legacy_database(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    command.upgrade(_alembic_config(database_url), "0001_initial_crm_schema")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO companies "
                "(id, name, domain, industry, employee_band, region) "
                "VALUES ('legacy-company', 'Legacy Co', 'legacy.example.com', "
                "'SaaS', '51-200', 'NA')"
            )
        )
        connection.execute(text("DROP TABLE alembic_version"))

    migrate_database(database_url)

    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT name FROM companies WHERE id = 'legacy-company'")
            ).scalar_one()
            == "Legacy Co"
        )
    assert _revision(database_url) == HEAD
    assert inspect(engine).has_table("approval_requests")


def test_migrate_database_stamps_an_existing_current_schema(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'current-unversioned.db'}"
    engine = create_engine(database_url)
    command.upgrade(_alembic_config(database_url), "0002_control_plane")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO companies "
                "(id, name, domain, industry, employee_band, region) "
                "VALUES ('current-company', 'Current Co', 'current.example.com', "
                "'SaaS', '51-200', 'NA')"
            )
        )

    migrate_database(database_url)

    assert _revision(database_url) == HEAD
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT name FROM companies WHERE id = 'current-company'")
            ).scalar_one()
            == "Current Co"
        )
