"""Persist canonical Sprint 3 Transaction DNA records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_transaction_dna"
down_revision: str | None = "0003_ucp_compliance"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transaction_dna",
        sa.Column(
            "case_id",
            sa.String(64),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("transaction_id", sa.String(64), nullable=False, unique=True),
        sa.Column("dna_fingerprint", sa.String(64), nullable=False),
        sa.Column("dna_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transaction_dna_fingerprint", "transaction_dna", ["dna_fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_transaction_dna_fingerprint", table_name="transaction_dna")
    op.drop_table("transaction_dna")
