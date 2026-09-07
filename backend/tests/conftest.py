import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Cart, Product, Region, User, UserRegion, UserRole

test_engine = create_engine(settings.test_database_url)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    outer_transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Support code-under-test calling session.commit() while still rolling
    # everything back at the end of the test (nested SAVEPOINT trick).
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, trans) -> None:  # noqa: ANN001
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def _get_test_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(
    db: Session,
    *,
    username: str,
    password: str,
    role: UserRole = UserRole.CUSTOMER,
    balance: float = 0,
    region: Region | None = Region.NAJAF,
    regions: list[Region] | None = None,
) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.title(),
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    # One wallet per region the account belongs to; `balance` seeds the first.
    for i, r in enumerate(regions if regions is not None else ([region] if region else [])):
        db.add(UserRegion(user_id=user.id, region=r, balance=balance if i == 0 else 0))
    db.add(Cart(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def customer(db: Session) -> User:
    return make_user(db, username=f"customer_{uuid.uuid4().hex[:8]}", password="password123", role=UserRole.CUSTOMER, balance=100_000)


@pytest.fixture()
def admin(db: Session) -> User:
    return make_user(db, username=f"admin_{uuid.uuid4().hex[:8]}", password="password123", role=UserRole.ADMIN, balance=100_000)


def make_product(
    db: Session,
    *,
    name: str = "Coca Cola",
    price: float = 2500,
    stock: int = 10,
    is_active: bool = True,
    region: Region | None = Region.NAJAF,
) -> Product:
    product = Product(
        name=name, description="A refreshing drink", price=price, stock_quantity=stock, is_active=is_active, region=region
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
