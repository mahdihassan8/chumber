from pydantic import BaseModel

from app.schemas.balance import BalanceTransactionRead
from app.schemas.order import OrderRead


class OverviewStats(BaseModel):
    total_users: int
    total_customers: int
    total_admins: int
    total_products: int
    available_products: int
    out_of_stock_products: int
    total_orders: int
    total_balance_distributed: float
    # Live aggregates, not stored figures: always computed fresh from the
    # ledger/product tables so they can never drift out of sync with a spend,
    # recharge, or stock change.
    total_user_balance: float
    total_inventory_value: float
    recent_orders: list[OrderRead]
    recent_transactions: list[BalanceTransactionRead]
