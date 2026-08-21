"""Persist immutable Sprint 7 officer decisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_human_review"
down_revision: str | None = "0005_investigation_state"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "officer_decisions",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column(
            "case_id", sa.String(64), sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("officer_id", sa.String(160), nullable=False),
        sa.Column("officer_role", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(comment) >= 10", name="ck_officer_decision_comment"),
    )
    op.create_index(
        "ix_officer_decisions_case_created", "officer_decisions", ["case_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_officer_decisions_case_created", table_name="officer_decisions")
    op.drop_table("officer_decisions")
