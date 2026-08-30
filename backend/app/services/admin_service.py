from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.repositories.balance_transaction_repository import BalanceTransactionRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import OverviewStats
from app.schemas.balance import BalanceTransactionRead
from app.schemas.order import OrderRead


def get_overview(db: Session) -> OverviewStats:
    user_repo = UserRepository(db)
    product_repo = ProductRepository(db)
    order_repo = OrderRepository(db)
    txn_repo = BalanceTransactionRepository(db)

    total_users = user_repo.count()
    total_customers = user_repo.count_by_role(UserRole.CUSTOMER)
    total_admins = user_repo.count_by_role(UserRole.ADMIN)

    total_products = product_repo.count()
    available_products = product_repo.count_available()
    out_of_stock_products = product_repo.count_out_of_stock()

    total_orders = order_repo.count()

    total_balance_distributed = txn_repo.sum_admin_recharges()

    recent_orders = order_repo.list_recent(10)
    recent_transactions = txn_repo.list_recent(10)

    return OverviewStats(
        total_users=total_users,
        total_customers=total_customers,
        total_admins=total_admins,
        total_products=total_products,
        available_products=available_products,
        out_of_stock_products=out_of_stock_products,
        total_orders=total_orders,
        total_balance_distributed=float(total_balance_distributed),
        recent_orders=[OrderRead.model_validate(o) for o in recent_orders],
        recent_transactions=[BalanceTransactionRead.model_validate(t) for t in recent_transactions],
    )
