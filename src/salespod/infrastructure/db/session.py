from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_BASE_REVISION = "0001_initial_crm_schema"
_CURRENT_BASELINE_REVISION = "0002_control_plane"
_LEGACY_TABLES = {
    "companies",
    "leads",
    "deals",
    "email_threads",
    "call_transcripts",
    "activities",
    "deal_stage_history",
}
_CONTROL_PLANE_TABLES = {"approval_requests", "audit_events"}


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True, pool_pre_ping=True)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=build_engine(database_url), autoflush=False, expire_on_commit=False)


def create_schema(database_url: str) -> None:
    """Apply all database migrations while retaining the historical API name."""
    migrate_database(database_url)


def migrate_database(database_url: str) -> None:
    """Upgrade a database to the latest revision, bootstrapping old local fixtures.

    Databases created before Alembic did not have an ``alembic_version`` table.
    A schema that is recognizably at the old CRM baseline is stamped at revision
    0001 and upgraded normally. A schema that already contains the current
    control-plane tables is stamped at head without touching its data.
    """
    engine = build_engine(database_url)
    config = _alembic_config(database_url, engine)
    revision = _database_revision(engine)

    if revision is not None:
        command.upgrade(config, "head")
        return

    schema_kind = _unversioned_schema_kind(engine)
    if schema_kind == "empty":
        command.upgrade(config, "head")
    elif schema_kind == "legacy":
        command.stamp(config, _BASE_REVISION)
        command.upgrade(config, "head")
    elif schema_kind == "current":
        # This is the pre-Alembic control-plane schema. Stamp it at the
        # control-plane baseline so subsequent revisions can add constraints
        # and indexes without rewriting existing CRM rows.
        command.stamp(config, _CURRENT_BASELINE_REVISION)
        command.upgrade(config, "head")
    else:  # pragma: no cover - defensive guard for an unsupported partial schema
        raise RuntimeError(
            "The database has an unsupported unversioned schema. "
            "Back it up and migrate it manually before starting Sales Pod."
        )


def reset_database(database_url: str) -> None:
    """Reset a database through Alembic, then recreate the latest schema."""
    migrate_database(database_url)
    engine = build_engine(database_url)
    config = _alembic_config(database_url, engine)
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def _alembic_config(database_url: str, engine: Engine) -> Config:
    config_path = Path(__file__).resolve().parents[4] / "alembic.ini"
    if not config_path.exists():
        raise RuntimeError(f"Alembic configuration was not found at {config_path}")
    config = Config(str(config_path))
    # ConfigParser treats percent signs as interpolation markers.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.attributes["connection"] = engine
    return config


def _database_revision(engine: Engine) -> str | None:
    inspector = inspect(engine)
    if not inspector.has_table("alembic_version"):
        return None
    with engine.connect() as connection:
        row = connection.exec_driver_sql("SELECT version_num FROM alembic_version").first()
    return str(row[0]) if row else None


def _unversioned_schema_kind(engine: Engine) -> str:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if not tables:
        return "empty"
    if not _LEGACY_TABLES.issubset(tables):
        return "unsupported"

    transcript_columns = {column["name"] for column in inspector.get_columns("call_transcripts")}
    has_control_plane = _CONTROL_PLANE_TABLES.issubset(tables)
    has_deal_links = "deal_id" in transcript_columns
    if has_control_plane and has_deal_links:
        return "current"
    if not has_control_plane:
        return "legacy"
    return "unsupported"
