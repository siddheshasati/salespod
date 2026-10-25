"""Align transcript deal-link indexes and constraints.

Revision ID: 0003_transcript_link_constraints
Revises: 0002_control_plane
Create Date: 2026-10-25
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect

revision: str = "0003_transcript_link_constraints"
down_revision: str | Sequence[str] | None = "0002_control_plane"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    index_names = {index["name"] for index in inspector.get_indexes("call_transcripts")}
    if "ix_call_transcripts_deal_id" not in index_names:
        op.create_index(
            "ix_call_transcripts_deal_id",
            "call_transcripts",
            ["deal_id"],
            unique=False,
        )

    foreign_keys = inspector.get_foreign_keys("call_transcripts")
    has_deal_foreign_key = any(
        foreign_key["constrained_columns"] == ["deal_id"]
        and foreign_key["referred_table"] == "deals"
        and foreign_key["referred_columns"] == ["id"]
        for foreign_key in foreign_keys
    )
    if not has_deal_foreign_key:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("call_transcripts") as batch_op:
                batch_op.create_foreign_key(
                    "fk_call_transcripts_deal_id_deals",
                    "deals",
                    ["deal_id"],
                    ["id"],
                )
        else:
            op.create_foreign_key(
                "fk_call_transcripts_deal_id_deals",
                "call_transcripts",
                "deals",
                ["deal_id"],
                ["id"],
            )


def downgrade() -> None:
    op.drop_index("ix_call_transcripts_deal_id", table_name="call_transcripts")
