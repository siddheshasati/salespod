"""Add transcript deal links, approvals, and audit events.

Revision ID: 0002_control_plane
Revises: 0001_initial_crm_schema
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0002_control_plane"
down_revision: str | Sequence[str] | None = "0001_initial_crm_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    transcript_columns = {column["name"] for column in inspector.get_columns("call_transcripts")}
    if "deal_id" not in transcript_columns:
        op.add_column(
            "call_transcripts",
            sa.Column("deal_id", sa.String(length=36), nullable=True),
        )
    index_names = {index["name"] for index in inspector.get_indexes("call_transcripts")}
    if "ix_call_transcripts_deal_id" not in index_names:
        op.create_index(
            "ix_call_transcripts_deal_id",
            "call_transcripts",
            ["deal_id"],
            unique=False,
        )

    if not inspector.has_table("approval_requests"):
        op.create_table(
            "approval_requests",
            sa.Column("id", sa.String(length=120), nullable=False),
            sa.Column("risk_type", sa.String(length=80), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("source_type", sa.String(length=80), nullable=False),
            sa.Column("source_id", sa.String(length=36), nullable=False),
            sa.Column("deal_id", sa.String(length=36), nullable=False),
            sa.Column("company_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decided_by", sa.String(length=120), nullable=True),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("risk_type", "source_id", name="uq_approval_requests_risk_source"),
        )
    index_names = {index["name"] for index in inspector.get_indexes("approval_requests")}
    if "ix_approval_requests_status" not in index_names:
        op.create_index(
            "ix_approval_requests_status",
            "approval_requests",
            ["status"],
            unique=False,
        )
    if "ix_approval_requests_deal_id" not in index_names:
        op.create_index(
            "ix_approval_requests_deal_id",
            "approval_requests",
            ["deal_id"],
            unique=False,
        )

    if not inspector.has_table("audit_events"):
        op.create_table(
            "audit_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("actor", sa.String(length=120), nullable=False),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.String(length=120), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    index_names = {index["name"] for index in inspector.get_indexes("audit_events")}
    if "ix_audit_events_occurred_at" not in index_names:
        op.create_index(
            "ix_audit_events_occurred_at",
            "audit_events",
            ["occurred_at"],
            unique=False,
        )
    if "ix_audit_events_entity" not in index_names:
        op.create_index(
            "ix_audit_events_entity",
            "audit_events",
            ["entity_type", "entity_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_approval_requests_deal_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_table("approval_requests")
    index_names = {
        index["name"] for index in inspect(op.get_bind()).get_indexes("call_transcripts")
    }
    if "ix_call_transcripts_deal_id" in index_names:
        op.drop_index("ix_call_transcripts_deal_id", table_name="call_transcripts")
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("call_transcripts") as batch_op:
            batch_op.drop_column("deal_id")
    else:
        op.drop_column("call_transcripts", "deal_id")
