"""Add Sprint 1 document intelligence persistence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_document_intelligence"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("filename", sa.String(255), nullable=False, server_default="document"),
    )
    op.add_column(
        "documents", sa.Column("content_hash", sa.String(64), nullable=False, server_default="")
    )
    op.add_column(
        "documents",
        sa.Column("mime_type", sa.String(64), nullable=False, server_default="application/pdf"),
    )
    op.add_column("documents", sa.Column("overall_confidence", sa.Float()))
    op.add_column("documents", sa.Column("extraction_json", postgresql.JSONB()))
    op.add_column("documents", sa.Column("textract_job_id", sa.String(128)))
    op.add_column("documents", sa.Column("error_code", sa.String(64)))
    op.add_column("documents", sa.Column("advisory", sa.String(512)))
    op.create_unique_constraint(
        "uq_documents_case_content_hash", "documents", ["case_id", "content_hash"]
    )
    op.create_table(
        "document_registry",
        sa.Column("document_fingerprint", sa.String(128), primary_key=True),
        sa.Column("ibu_id", sa.String(64), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("document_registry")
    op.drop_constraint("uq_documents_case_content_hash", "documents", type_="unique")
    for column in (
        "advisory",
        "error_code",
        "textract_job_id",
        "extraction_json",
        "overall_confidence",
        "mime_type",
        "content_hash",
        "filename",
    ):
        op.drop_column("documents", column)
