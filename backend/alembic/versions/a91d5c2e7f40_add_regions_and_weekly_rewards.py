"""add Baghdad/Najaf regions and the Baghdad weekly reward

Revision ID: a91d5c2e7f40
Revises: e7b3f2a91c05
Create Date: 2026-09-07

Purely additive. Existing rows keep NULL regions — nothing is guessed or
back-filled here, because the data gives no signal about which region a
pre-existing user or product belongs to. A Super Admin assigns them from the
dashboard; until then they are treated as belonging to no region and are
excluded from region-scoped reads (fail closed).
"""

import sqlalchemy as sa
from alembic import op

revision = "a91d5c2e7f40"
down_revision = "e7b3f2a91c05"
branch_labels = None
depends_on = None

region_enum = sa.Enum("BAGHDAD", "NAJAF", name="region")


def upgrade() -> None:
    region_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("users", sa.Column("region", region_enum, nullable=True))
    op.create_index("ix_users_region", "users", ["region"])

    op.add_column("products", sa.Column("region", region_enum, nullable=True))
    op.create_index("ix_products_region", "products", ["region"])

    # A reward is its own kind of ledger entry, not an admin adjustment.
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'REWARD'")

    op.create_table(
        "weekly_rewards",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        # UNIQUE is the real "one reward per Tuesday" guarantee — see
        # WeeklyReward and reward_service.
        sa.Column("reward_date", sa.Date(), nullable=False, unique=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("weekly_rewards")

    op.drop_index("ix_products_region", table_name="products")
    op.drop_column("products", "region")

    op.drop_index("ix_users_region", table_name="users")
    op.drop_column("users", "region")

    region_enum.drop(op.get_bind(), checkfirst=True)

    # transaction_type keeps REWARD: Postgres cannot drop a single enum value,
    # and rebuilding the type would mean rewriting the ledger. An unused label
    # is harmless.
