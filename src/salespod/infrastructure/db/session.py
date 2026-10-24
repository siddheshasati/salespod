from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


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
    engine = build_engine(database_url)
    Base.metadata.create_all(engine)
    _add_legacy_columns(engine)


def _add_legacy_columns(engine: Engine) -> None:
    """Apply the small additive schema changes needed by existing local fixtures.

    Alembic is the right next step for multi-environment production migrations;
    this additive guard keeps an already-seeded SQLite demo usable while the
    project is still in its local vertical-slice stage.
    """
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(call_transcripts)").fetchall()
        }
        if "deal_id" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE call_transcripts ADD COLUMN deal_id VARCHAR(36)"
            )
