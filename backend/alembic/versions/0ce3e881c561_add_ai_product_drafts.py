"""add ai product drafts

Revision ID: 0ce3e881c561
Revises: fe51bcb6a09c
Create Date: 2026-09-16 12:21:10.152065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0ce3e881c561'
down_revision: Union[str, None] = 'fe51bcb6a09c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The status column reuses the `ai_request_status` type that the
# ai_restock_requests migration already created. create_type=False is
# load-bearing: without it this migration emits CREATE TYPE for a type that
# exists and dies with DuplicateObject — the same trap the chumber_requirements
# migration hit with the region enum.
ai_request_status = postgresql.ENUM(
    'PENDING', 'CONFIRMED', 'REJECTED', 'FAILED', name='ai_request_status', create_type=False
)

# NOTE: autogenerate also reported unrelated pre-existing drift (NOT NULL on
# user_regions.created_at / weekly_rewards.created_at, an index on
# weekly_rewards.region). Left out deliberately — out of scope here and
# untested against the real data in those columns.


def upgrade() -> None:
    op.create_table('ai_product_drafts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('admin_id', sa.UUID(), nullable=False),
    sa.Column('requested_name', sa.String(length=200), nullable=False),
    sa.Column('source_url', sa.String(length=1000), nullable=True),
    sa.Column('source_title', sa.String(length=500), nullable=True),
    sa.Column('extracted_name', sa.String(length=200), nullable=True),
    sa.Column('extracted_description', sa.Text(), nullable=True),
    sa.Column('suggested_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('image_prompt', sa.Text(), nullable=True),
    sa.Column('staged_image_url', sa.String(length=500), nullable=True),
    sa.Column('has_transparency', sa.Boolean(), nullable=False),
    sa.Column('status', ai_request_status, nullable=False),
    sa.Column('error_message', sa.String(length=500), nullable=True),
    sa.Column('created_product_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['created_product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Only the table is dropped: ai_request_status is still in use by
    # ai_restock_requests, so it must outlive this migration.
    op.drop_table('ai_product_drafts')
