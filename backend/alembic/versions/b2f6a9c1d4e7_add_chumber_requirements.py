"""add chumber_requirements table

Revision ID: b2f6a9c1d4e7
Revises: d3f81a4b6c92
Create Date: 2026-09-08

One editable "Chumber required" amount/note per region, backing the Admin
Dashboard's new Chumber Required section. No seed rows: the row is
get-or-created lazily on first read/write per region, same pattern as
UserRegion memberships.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b2f6a9c1d4e7"
down_revision = "d3f81a4b6c92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chumber_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # create_type=False: the "region" enum type already exists (created by
        # d3f81a4b6c92) and is shared with users/products -- this column must
        # reuse it, not attempt to CREATE TYPE region a second time.
        sa.Column("region", postgresql.ENUM("baghdad", "najaf", name="region", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("region", name="uq_chumber_requirement_region"),
    )
    op.create_index("ix_chumber_requirements_region", "chumber_requirements", ["region"])


def downgrade() -> None:
    op.drop_index("ix_chumber_requirements_region", table_name="chumber_requirements")
    op.drop_table("chumber_requirements")
