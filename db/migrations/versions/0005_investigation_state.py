"""Persist Sprint 6 investigation graph snapshots."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_investigation_state"
down_revision: str | None = "0004_transaction_dna"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("cases", "status", type_=sa.String(64), existing_type=sa.String(32))
    op.create_table(
        "investigation_states",
        sa.Column(
            "case_id",
            sa.String(64),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("state_json", postgresql.JSONB(), nullable=False),
        sa.Column("workflow_status", sa.String(32), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("investigation_states")
    op.alter_column("cases", "status", type_=sa.String(32), existing_type=sa.String(64))
