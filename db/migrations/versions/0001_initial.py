"""Create cases, documents, and append-only audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("ibu_id", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("case_id", sa.String(64), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("document_type", sa.String(64)),
        sa.Column("s3_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_documents_case_id", "documents", ["case_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("case_id", sa.String(64), sa.ForeignKey("cases.id")),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_ref", sa.String(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_events_case_created", "audit_events", ["case_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("documents")
    op.drop_table("cases")
