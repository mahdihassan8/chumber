"""add SUPER_ADMIN to the user_role enum

Revision ID: e7b3f2a91c05
Revises: c4a1e9d70b31
Create Date: 2026-09-07

Adds the new value only — no row is moved to it here. Postgres forbids using a
freshly added enum value in the same transaction that added it, and the
bootstrap Super Admin is established separately at startup by
app.db.seed.seed_bootstrap_admin, which runs in its own transaction.
"""

from alembic import op

revision = "e7b3f2a91c05"
down_revision = "c4a1e9d70b31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS keeps this safe to re-run against a database where the
    # value was already added by hand.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'SUPER_ADMIN'")


def downgrade() -> None:
    # Postgres cannot drop a single enum value, so the type is rebuilt without
    # it. Any Super Admin is demoted to ADMIN first, otherwise the cast below
    # would fail on a value the new type doesn't have.
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'SUPER_ADMIN'")
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('CUSTOMER', 'ADMIN')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::text::user_role"
    )
    op.execute("DROP TYPE user_role_old")
