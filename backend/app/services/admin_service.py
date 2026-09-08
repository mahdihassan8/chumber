from sqlalchemy.orm import Session

from app.models.user import Region, User, UserRole
from app.repositories.balance_transaction_repository import BalanceTransactionRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import OverviewStats
from app.schemas.balance import BalanceTransactionRead
from app.schemas.order import OrderRead
from app.services import chumber_requirement_service, total_debt_service


def get_overview(db: Session, region: Region | None) -> OverviewStats:
    user_repo = UserRepository(db)
    product_repo = ProductRepository(db)
    order_repo = OrderRepository(db)
    txn_repo = BalanceTransactionRepository(db)

    total_users = user_repo.count(region)
    total_customers = user_repo.count_by_role(UserRole.CUSTOMER, region)
    total_admins = user_repo.count_by_role(UserRole.ADMIN, region)

    total_products = product_repo.count(region)
    available_products = product_repo.count_available(region)
    out_of_stock_products = product_repo.count_out_of_stock(region)

    total_orders = order_repo.count(region)

    total_balance_distributed = txn_repo.sum_admin_recharges(region)
    total_user_balance = user_repo.sum_balances(region)
    total_inventory_value = product_repo.sum_inventory_value(region)
    total_debts = total_debt_service.sum_debts(db, region)
    chumber_required_total = chumber_requirement_service.sum_amount(db, region)
    balance_difference = total_user_balance + chumber_required_total - total_inventory_value

    recent_orders = order_repo.list_recent(10, region)
    recent_transactions = txn_repo.list_recent(10, region)

    return OverviewStats(
        total_users=total_users,
        total_customers=total_customers,
        total_admins=total_admins,
        total_products=total_products,
        available_products=available_products,
        out_of_stock_products=out_of_stock_products,
        total_orders=total_orders,
        total_balance_distributed=float(total_balance_distributed),
        total_user_balance=total_user_balance,
        total_inventory_value=total_inventory_value,
        total_debts=total_debts,
        balance_difference=balance_difference,
        recent_orders=[OrderRead.model_validate(o) for o in recent_orders],
        recent_transactions=[BalanceTransactionRead.model_validate(t) for t in recent_transactions],
    )
