"""add currency to balance transactions

Revision ID: f8ee6b0e36f1
Revises: ba748a01a8af
Create Date: 2026-08-29 12:21:15.649344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8ee6b0e36f1'
down_revision: Union[str, None] = 'ba748a01a8af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    currency_enum = sa.Enum('USD', 'IQD', name='currency')
    currency_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('balance_transactions', sa.Column('currency', currency_enum, server_default='USD', nullable=False))


def downgrade() -> None:
    op.drop_column('balance_transactions', 'currency')
    sa.Enum(name='currency').drop(op.get_bind(), checkfirst=True)
