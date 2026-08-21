"""Harden the append-only audit trail for Sprint 8."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_security_audit"
down_revision: str | None = "0006_human_review"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "officer_decisions",
        sa.Column("idempotency_key_hash", sa.String(64), nullable=True),
    )
    op.execute(
        "UPDATE officer_decisions SET idempotency_key_hash = md5(id) || md5(id || 'legacy')"
    )
    op.alter_column("officer_decisions", "idempotency_key_hash", nullable=False)
    op.create_unique_constraint(
        "uq_officer_decision_idempotency",
        "officer_decisions",
        ["case_id", "idempotency_key_hash"],
    )
    op.alter_column("audit_events", "id", new_column_name="event_id")
    op.add_column("audit_events", sa.Column("correlation_id", sa.String(128), nullable=False, server_default="system"))
    op.add_column("audit_events", sa.Column("ibu_id", sa.String(64), nullable=False, server_default="system"))
    op.add_column("audit_events", sa.Column("actor_role", sa.String(40), nullable=False, server_default="SYSTEM"))
    op.add_column("audit_events", sa.Column("ip_address", sa.String(80), nullable=False, server_default="system"))
    op.add_column("audit_events", sa.Column("user_agent", sa.String(256), nullable=False, server_default="system"))
    op.create_index("ix_audit_events_ibu_created", "audit_events", ["ibu_id", "created_at"])
    op.execute(
        """CREATE FUNCTION reject_audit_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit_events is append-only'; END; $$ LANGUAGE plpgsql"""
    )
    op.execute(
        """CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation()"""
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS reject_audit_mutation")
    op.drop_index("ix_audit_events_ibu_created", table_name="audit_events")
    for column in ("user_agent", "ip_address", "actor_role", "ibu_id", "correlation_id"):
        op.drop_column("audit_events", column)
    op.alter_column("audit_events", "event_id", new_column_name="id")
    op.drop_constraint(
        "uq_officer_decision_idempotency", "officer_decisions", type_="unique"
    )
    op.drop_column("officer_decisions", "idempotency_key_hash")
