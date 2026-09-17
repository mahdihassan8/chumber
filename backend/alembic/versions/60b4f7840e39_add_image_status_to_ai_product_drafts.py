"""add image status to ai product drafts

Revision ID: 60b4f7840e39
Revises: 0ce3e881c561
Create Date: 2026-09-17 10:31:55.976730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '60b4f7840e39'
down_revision: Union[str, None] = '0ce3e881c561'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# NOTE: autogenerate also reported the same unrelated pre-existing drift as
# earlier migrations (NOT NULL on user_regions.created_at /
# weekly_rewards.created_at, an index on weekly_rewards.region). Left out
# deliberately - out of scope and untested against the real data there.


def upgrade() -> None:
    # server_default matters: image_status is NOT NULL, so without it this
    # fails on any table that already has rows.
    op.add_column(
        'ai_product_drafts',
        sa.Column('image_status', sa.String(length=30), nullable=False, server_default='not_attempted'),
    )
    op.add_column('ai_product_drafts', sa.Column('image_error', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('ai_product_drafts', 'image_error')
    op.drop_column('ai_product_drafts', 'image_status')
