from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import auth_headers


def test_login_success(client: TestClient, customer: User) -> None:
    response = client.post("/api/auth/login", json={"username": customer.username, "password": "password123"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["username"] == customer.username
    assert body["user"]["role"] == "customer"


def test_login_wrong_password(client: TestClient, customer: User) -> None:
    response = client.post("/api/auth/login", json={"username": customer.username, "password": "wrong-password"})
    assert response.status_code == 401


def test_login_unknown_user(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "nobody", "password": "password123"})
    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(customer.id)


def test_inactive_user_cannot_login(client: TestClient, db: Session, customer: User) -> None:
    customer.is_active = False
    db.commit()
    response = client.post("/api/auth/login", json={"username": customer.username, "password": "password123"})
    assert response.status_code == 401


def test_login_token_lasts_seven_days(client: TestClient, customer: User) -> None:
    from datetime import datetime, timedelta, timezone

    from jose import jwt as jose_jwt

    from app.core.config import settings

    response = client.post("/api/auth/login", json={"username": customer.username, "password": "password123"})
    token = response.json()["access_token"]
    payload = jose_jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    expected = datetime.now(timezone.utc) + timedelta(days=7)
    assert abs((expires_at - expected).total_seconds()) < 60  # allow test execution slack
    assert payload["tv"] == customer.token_version


def test_changing_password_invalidates_existing_session(client: TestClient, customer: User) -> None:
    old_headers = auth_headers(client, customer.username, "password123")

    # the old token works until the password changes
    assert client.get("/api/auth/me", headers=old_headers).status_code == 200

    change_resp = client.post(
        "/api/users/me/password",
        json={"current_password": "password123", "new_password": "newpassword456"},
        headers=old_headers,
    )
    assert change_resp.status_code == 200

    # the pre-change token must now be rejected, even though it hasn't expired
    assert client.get("/api/auth/me", headers=old_headers).status_code == 401

    # logging in again with the new password issues a token that works
    new_headers = auth_headers(client, customer.username, "newpassword456")
    assert client.get("/api/auth/me", headers=new_headers).status_code == 200


def test_admin_reset_password_invalidates_target_users_session(client: TestClient, customer: User, admin: User) -> None:
    customer_headers = auth_headers(client, customer.username, "password123")
    assert client.get("/api/auth/me", headers=customer_headers).status_code == 200

    admin_headers = auth_headers(client, admin.username, "password123")
    reset_resp = client.post(f"/api/users/{customer.id}/password", json={"new_password": "resetbyadmin1"}, headers=admin_headers)
    assert reset_resp.status_code == 200

    # the customer's pre-reset token is now invalid
    assert client.get("/api/auth/me", headers=customer_headers).status_code == 401
    # the admin's own session is unaffected — only the target user's tokens are invalidated
    assert client.get("/api/auth/me", headers=admin_headers).status_code == 200
