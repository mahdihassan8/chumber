"""remove total_debts table

Revision ID: e91c3a7d5f42
Revises: d4a1e9f27b83
Create Date: 2026-09-08

The Total Debts feature has been removed entirely (superseded by Chumber
Required, which the Balance Difference calculation now uses instead). This
table was only ever used to back that feature -- nothing else references it,
so it is safe to drop outright.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e91c3a7d5f42"
down_revision = "d4a1e9f27b83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_total_debts_region", table_name="total_debts")
    op.drop_table("total_debts")


def downgrade() -> None:
    op.create_table(
        "total_debts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # create_type=False: the "region" enum type is shared with
        # users/products/chumber_requirements and must not be re-created.
        sa.Column("region", postgresql.ENUM("baghdad", "najaf", name="region", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("region", name="uq_total_debt_region"),
    )
    op.create_index("ix_total_debts_region", "total_debts", ["region"])
