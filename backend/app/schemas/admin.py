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
    recent_orders: list[OrderRead]
    recent_transactions: list[BalanceTransactionRead]
