"""multi-region membership + per-region balances; existing data becomes NAJAF

Revision ID: d3f81a4b6c92
Revises: a91d5c2e7f40
Create Date: 2026-09-07

The previous revision modelled a single `users.region`. The final rules require
a user to be able to belong to one *or two* regions, with completely separate
money in each. That means membership becomes a row, and the balance moves onto
that row so it is impossible for one region's balance to be read as another's.

Nothing is deleted. Every existing account, product, order and ledger row is
declared NAJAF (the pre-existing system *is* Najaf), and each account's current
balance is carried across verbatim into its Najaf membership row.

Downgrade rebuilds users.region/users.balance from the Najaf rows, so the
transformation is reversible.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d3f81a4b6c92"
down_revision = "a91d5c2e7f40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- 1. existing data is Najaf ------------------------------------------
    op.execute("UPDATE users SET region = 'NAJAF' WHERE region IS NULL")
    op.execute("UPDATE products SET region = 'NAJAF' WHERE region IS NULL")

    # ---- 2. membership + per-region balance ---------------------------------
    op.create_table(
        "user_regions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("region", postgresql.ENUM("BAGHDAD", "NAJAF", name="region", create_type=False), nullable=False),
        # The account balance *for that region*, in IQD. Independent per row —
        # this is what keeps a dual-region user's two wallets from ever mixing.
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        # One membership per user per region; also the natural upsert key.
        sa.UniqueConstraint("user_id", "region", name="uq_user_region"),
    )
    op.create_index("ix_user_regions_user_id", "user_regions", ["user_id"])
    op.create_index("ix_user_regions_region", "user_regions", ["region"])

    # Every existing account becomes a Najaf member, carrying its balance over.
    op.execute(
        """
        INSERT INTO user_regions (id, user_id, region, balance)
        SELECT gen_random_uuid(), id, 'NAJAF', balance FROM users
        """
    )
    # A Super Admin is global, so it also gets a Baghdad wallet (starting at 0)
    # — its Najaf money stays exactly where it was.
    op.execute(
        """
        INSERT INTO user_regions (id, user_id, region, balance)
        SELECT gen_random_uuid(), id, 'BAGHDAD', 0 FROM users WHERE role = 'SUPER_ADMIN'
        """
    )

    # ---- 3. money and orders carry their own region --------------------------
    # Derived columns would be ambiguous once a user belongs to two regions, so
    # each row records the region it actually happened in.
    op.add_column("orders", sa.Column("region", postgresql.ENUM("BAGHDAD", "NAJAF", name="region", create_type=False), nullable=True))
    op.execute("UPDATE orders SET region = 'NAJAF' WHERE region IS NULL")
    op.alter_column("orders", "region", nullable=False)
    op.create_index("ix_orders_region", "orders", ["region"])

    op.add_column(
        "balance_transactions", sa.Column("region", postgresql.ENUM("BAGHDAD", "NAJAF", name="region", create_type=False), nullable=True)
    )
    op.execute("UPDATE balance_transactions SET region = 'NAJAF' WHERE region IS NULL")
    op.alter_column("balance_transactions", "region", nullable=False)
    op.create_index("ix_balance_transactions_region", "balance_transactions", ["region"])

    # ---- 4. rewards are per region ------------------------------------------
    op.add_column(
        "weekly_rewards", sa.Column("region", postgresql.ENUM("BAGHDAD", "NAJAF", name="region", create_type=False), nullable=True)
    )
    op.execute("UPDATE weekly_rewards SET region = 'BAGHDAD' WHERE region IS NULL")
    op.alter_column("weekly_rewards", "region", nullable=False)
    # "One reward per Tuesday" becomes "one per Tuesday per region" — still a
    # DB constraint, so concurrent runs still cannot double-award.
    op.drop_constraint("weekly_rewards_reward_date_key", "weekly_rewards", type_="unique")
    op.create_unique_constraint("uq_weekly_reward_date_region", "weekly_rewards", ["reward_date", "region"])

    # ---- 5. retire the single-value columns ----------------------------------
    # Their content now lives in user_regions; leaving them would create a
    # second, silently-diverging source of truth for money.
    op.drop_index("ix_users_region", table_name="users")
    op.drop_column("users", "region")
    op.drop_column("users", "balance")


def downgrade() -> None:
    op.add_column("users", sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("region", postgresql.ENUM("BAGHDAD", "NAJAF", name="region", create_type=False), nullable=True))
    op.create_index("ix_users_region", "users", ["region"])
    # Restore from the Najaf membership, which is where the original values went.
    op.execute(
        """
        UPDATE users u
        SET balance = ur.balance, region = ur.region
        FROM user_regions ur
        WHERE ur.user_id = u.id AND ur.region = 'NAJAF'
        """
    )

    op.drop_constraint("uq_weekly_reward_date_region", "weekly_rewards", type_="unique")
    op.create_unique_constraint("weekly_rewards_reward_date_key", "weekly_rewards", ["reward_date"])
    op.drop_column("weekly_rewards", "region")

    op.drop_index("ix_balance_transactions_region", table_name="balance_transactions")
    op.drop_column("balance_transactions", "region")

    op.drop_index("ix_orders_region", table_name="orders")
    op.drop_column("orders", "region")

    op.drop_index("ix_user_regions_region", table_name="user_regions")
    op.drop_index("ix_user_regions_user_id", table_name="user_regions")
    op.drop_table("user_regions")
