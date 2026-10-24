"""Create the original CRM schema.

Revision ID: 0001_initial_crm_schema
Revises:
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_crm_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("domain", sa.String(length=200), nullable=False),
        sa.Column("industry", sa.String(length=120), nullable=False),
        sa.Column("employee_band", sa.String(length=40), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain", name="uq_companies_domain"),
    )
    op.create_table(
        "leads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_leads_email"),
    )
    op.create_index("ix_leads_company_id", "leads", ["company_id"], unique=False)
    op.create_index("ix_leads_status", "leads", ["status"], unique=False)
    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("primary_lead_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("stage", sa.String(length=30), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("close_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stage_entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["primary_lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deals_company_id", "deals", ["company_id"], unique=False)
    op.create_index("ix_deals_stage", "deals", ["stage"], unique=False)
    op.create_index("ix_deals_close_date", "deals", ["close_date"], unique=False)
    op.create_table(
        "email_threads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("reply_status", sa.String(length=30), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_threads_company_id", "email_threads", ["company_id"], unique=False)
    op.create_index("ix_email_threads_lead_id", "email_threads", ["lead_id"], unique=False)
    op.create_index(
        "ix_email_threads_last_message_at",
        "email_threads",
        ["last_message_at"],
        unique=False,
    )
    op.create_table(
        "call_transcripts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_steps", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_call_transcripts_company_id",
        "call_transcripts",
        ["company_id"],
        unique=False,
    )
    op.create_index("ix_call_transcripts_lead_id", "call_transcripts", ["lead_id"], unique=False)
    op.create_table(
        "activities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("deal_id", sa.String(length=36), nullable=True),
        sa.Column("activity_type", sa.String(length=30), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_activities_idempotency_key"),
    )
    op.create_index("ix_activities_deal_id", "activities", ["deal_id"], unique=False)
    op.create_index("ix_activities_occurred_at", "activities", ["occurred_at"], unique=False)
    op.create_table(
        "deal_stage_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("deal_id", sa.String(length=36), nullable=False),
        sa.Column("from_stage", sa.String(length=30), nullable=True),
        sa.Column("to_stage", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stage_history_deal_id", "deal_stage_history", ["deal_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stage_history_deal_id", table_name="deal_stage_history")
    op.drop_table("deal_stage_history")
    op.drop_index("ix_activities_occurred_at", table_name="activities")
    op.drop_index("ix_activities_deal_id", table_name="activities")
    op.drop_table("activities")
    op.drop_index("ix_call_transcripts_lead_id", table_name="call_transcripts")
    op.drop_index("ix_call_transcripts_company_id", table_name="call_transcripts")
    op.drop_table("call_transcripts")
    op.drop_index("ix_email_threads_last_message_at", table_name="email_threads")
    op.drop_index("ix_email_threads_lead_id", table_name="email_threads")
    op.drop_index("ix_email_threads_company_id", table_name="email_threads")
    op.drop_table("email_threads")
    op.drop_index("ix_deals_close_date", table_name="deals")
    op.drop_index("ix_deals_stage", table_name="deals")
    op.drop_index("ix_deals_company_id", table_name="deals")
    op.drop_table("deals")
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_company_id", table_name="leads")
    op.drop_table("leads")
    op.drop_table("companies")
