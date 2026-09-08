"""add transfers table

Revision ID: d4a1e9f27b83
Revises: c8e1f4a06b3d
Create Date: 2026-09-08

User-to-user money transfers. Each row is a single already-completed,
atomically-applied movement of money from one account's regional wallet to
another's within the same region -- see app.services.transfer_service.send,
which locks both wallets and either commits both legs or rolls back the
whole transaction. sender_id/recipient_id are nullable and blanked (never the
row deleted) if either account is later permanently deleted, mirroring
balance_transactions.created_by_id -- this row is shared history between two
people, not exclusively either one's data.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d4a1e9f27b83"
down_revision = "c8e1f4a06b3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        # create_type=False: the "region" enum type already exists (from
        # d3f81a4b6c92) and is shared with users/products/chumber_requirements/
        # total_debts -- this column must reuse it, not CREATE TYPE region again.
        sa.Column("region", postgresql.ENUM("baghdad", "najaf", name="region", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        # Brand new type -- no existing "transfer_status" enum to collide with,
        # so this is fine to let SQLAlchemy CREATE TYPE for.
        sa.Column("status", sa.Enum("COMPLETED", name="transfer_status"), nullable=False, server_default="COMPLETED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_transfers_sender_id", "transfers", ["sender_id"])
    op.create_index("ix_transfers_recipient_id", "transfers", ["recipient_id"])
    op.create_index("ix_transfers_region", "transfers", ["region"])


def downgrade() -> None:
    op.drop_index("ix_transfers_region", table_name="transfers")
    op.drop_index("ix_transfers_recipient_id", table_name="transfers")
    op.drop_index("ix_transfers_sender_id", table_name="transfers")
    op.drop_table("transfers")
    op.execute("DROP TYPE transfer_status")
