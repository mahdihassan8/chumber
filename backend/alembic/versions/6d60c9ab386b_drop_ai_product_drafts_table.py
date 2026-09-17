"""drop ai product drafts table

Revision ID: 6d60c9ab386b
Revises: 60b4f7840e39
Create Date: 2026-09-17 11:25:07.855147

The automatic AI product-image workflow (Google Custom Search image
discovery, GTA-style filtering, rembg background removal) has been removed:
it was unused and its external image-search dependency was never configured
in production. ai_product_drafts existed only to support that workflow's
review/confirm screen, so it goes with it.

Nothing else depends on this table: Product has no foreign key pointing at
it (the reference runs the other way, ai_product_drafts.created_product_id
-> products.id), so dropping it cannot orphan or affect any product, order,
or uploaded image file. The ai_request_status enum this table's status
column used is left alone — ai_restock_requests (the separate, unrelated AI
restocking assistant) still uses it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6d60c9ab386b'
down_revision: Union[str, None] = '60b4f7840e39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Reused, not recreated: this is the same ai_request_status type
# ai_restock_requests already owns. create_type=False on both sides means
# neither direction of this migration touches the type itself.
ai_request_status = postgresql.ENUM(
    'PENDING', 'CONFIRMED', 'REJECTED', 'FAILED', name='ai_request_status', create_type=False
)


def upgrade() -> None:
    op.drop_table('ai_product_drafts')


def downgrade() -> None:
    op.create_table(
        'ai_product_drafts',
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
        sa.Column('image_status', sa.String(length=30), nullable=False, server_default='not_attempted'),
        sa.Column('image_error', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
