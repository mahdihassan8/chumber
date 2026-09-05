"""convert money columns from USD to IQD and drop the per-user currency

The app now has exactly one stored money unit: Iraqi Dinar. The shopper-facing
UI converts to Beans for display only (250 IQD = 1 Bean); the Admin Dashboard
shows raw IQD.

Conversion factor is 1000: the old display rate was 1 USD = 4 Beans, and the
new one is 1000 IQD = 4 Beans, so multiplying every stored USD figure by 1000
leaves every customer-visible Beans amount — and every price relative to every
balance — exactly as it was. Nothing is revalued by this migration.

The users.currency column (USD/IQD) and its enum type go away with it: with USD
gone there is only one currency, so the column carried no information.

Revision ID: c4a1e9d70b31
Revises: fda8ee6c9fdb
"""

from alembic import op
import sqlalchemy as sa

revision = "c4a1e9d70b31"
down_revision = "fda8ee6c9fdb"
branch_labels = None
depends_on = None

USD_TO_IQD = 1000

# (table, column) for every stored money figure in the schema.
MONEY_COLUMNS = [
    ("products", "price"),
    ("users", "balance"),
    ("orders", "total_amount"),
    ("order_items", "unit_price"),
    ("order_items", "subtotal"),
    ("balance_transactions", "amount"),
]


def upgrade() -> None:
    for table, column in MONEY_COLUMNS:
        op.execute(f"UPDATE {table} SET {column} = {column} * {USD_TO_IQD}")

    op.drop_column("users", "currency")
    sa.Enum(name="currency").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    currency_enum = sa.Enum("USD", "IQD", name="currency")
    currency_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("currency", currency_enum, server_default="USD", nullable=False),
    )

    for table, column in MONEY_COLUMNS:
        op.execute(f"UPDATE {table} SET {column} = {column} / {USD_TO_IQD}")
