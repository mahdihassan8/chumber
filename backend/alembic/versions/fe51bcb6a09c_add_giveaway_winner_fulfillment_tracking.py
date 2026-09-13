"""add giveaway winner fulfillment tracking

Revision ID: fe51bcb6a09c
Revises: e91c3a7d5f42
Create Date: 2026-09-13 12:07:51.501430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'fe51bcb6a09c'
down_revision: Union[str, None] = 'e91c3a7d5f42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOTE: autogenerate also picked up unrelated pre-existing drift (NOT NULL on
# user_regions.created_at / weekly_rewards.created_at, an index on
# weekly_rewards.region) — left out here since it's out of scope for this
# change and untested against the real data in those columns.


def upgrade() -> None:
    op.add_column('giveaway_winners', sa.Column('fulfilled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('giveaway_winners', sa.Column('fulfilled_by_admin_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_giveaway_winners_fulfilled_by_admin_id_users',
        'giveaway_winners', 'users', ['fulfilled_by_admin_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_giveaway_winners_fulfilled_by_admin_id_users', 'giveaway_winners', type_='foreignkey')
    op.drop_column('giveaway_winners', 'fulfilled_by_admin_id')
    op.drop_column('giveaway_winners', 'fulfilled_at')
