"""add total_debts table

Revision ID: c8e1f4a06b3d
Revises: b2f6a9c1d4e7
Create Date: 2026-09-08

One editable "total debts" amount per region, backing the Admin Dashboard's
new Total Debts section and the Balance Difference calculation. Same shape
as chumber_requirements: get-or-created lazily per region, no seed rows.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c8e1f4a06b3d"
down_revision = "b2f6a9c1d4e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "total_debts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # create_type=False: the "region" enum type already exists (from
        # d3f81a4b6c92) and is shared with users/products/chumber_requirements
        # -- this column must reuse it, not CREATE TYPE region again.
        sa.Column("region", postgresql.ENUM("baghdad", "najaf", name="region", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("region", name="uq_total_debt_region"),
    )
    op.create_index("ix_total_debts_region", "total_debts", ["region"])


def downgrade() -> None:
    op.drop_index("ix_total_debts_region", table_name="total_debts")
    op.drop_table("total_debts")
