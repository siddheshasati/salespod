"""Add durable company signal events.

Revision ID: 0004_signal_events
Revises: 0003_transcript_link_constraints
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0004_signal_events"
down_revision: str | Sequence[str] | None = "0003_transcript_link_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("signal_events"):
        op.create_table(
            "signal_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("company_id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("headline", sa.String(length=240), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("source", sa.String(length=80), nullable=False),
            sa.Column("source_url", sa.String(length=500), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("relevance_score", sa.Integer(), nullable=False),
            sa.Column("suggested_action", sa.Text(), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    index_names = {index["name"] for index in inspect(op.get_bind()).get_indexes("signal_events")}
    for index_name, column_name in (
        ("ix_signal_events_company_id", "company_id"),
        ("ix_signal_events_event_type", "event_type"),
        ("ix_signal_events_status", "status"),
        ("ix_signal_events_occurred_at", "occurred_at"),
    ):
        if index_name not in index_names:
            op.create_index(index_name, "signal_events", [column_name], unique=False)


def downgrade() -> None:
    op.drop_index("ix_signal_events_occurred_at", table_name="signal_events")
    op.drop_index("ix_signal_events_status", table_name="signal_events")
    op.drop_index("ix_signal_events_event_type", table_name="signal_events")
    op.drop_index("ix_signal_events_company_id", table_name="signal_events")
    op.drop_table("signal_events")
