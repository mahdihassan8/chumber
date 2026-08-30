from fastapi.testclient import TestClient

from app.models.user import User
from tests.conftest import auth_headers


def test_user_can_change_own_password(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(
        "/api/users/me/password",
        json={"current_password": "password123", "new_password": "newpassword456"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message"]

    old_login = client.post("/api/auth/login", json={"username": customer.username, "password": "password123"})
    assert old_login.status_code == 401

    new_login = client.post("/api/auth/login", json={"username": customer.username, "password": "newpassword456"})
    assert new_login.status_code == 200


def test_change_password_wrong_current_password_fails(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(
        "/api/users/me/password",
        json={"current_password": "wrong-password", "new_password": "newpassword456"},
        headers=headers,
    )
    assert response.status_code == 400

    still_works = client.post("/api/auth/login", json={"username": customer.username, "password": "password123"})
    assert still_works.status_code == 200


def test_change_password_too_short_rejected(client: TestClient, customer: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(
        "/api/users/me/password",
        json={"current_password": "password123", "new_password": "short"},
        headers=headers,
    )
    assert response.status_code == 422


def test_change_password_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/users/me/password", json={"current_password": "x", "new_password": "newpassword456"}
    )
    assert response.status_code == 401


def test_admin_can_reset_user_password(client: TestClient, admin: User, customer: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(f"/api/users/{customer.id}/password", json={"new_password": "resetbyadmin1"}, headers=headers)
    assert response.status_code == 200

    new_login = client.post("/api/auth/login", json={"username": customer.username, "password": "resetbyadmin1"})
    assert new_login.status_code == 200

    old_login = client.post("/api/auth/login", json={"username": customer.username, "password": "password123"})
    assert old_login.status_code == 401


def test_customer_cannot_reset_password(client: TestClient, customer: User, admin: User) -> None:
    headers = auth_headers(client, customer.username, "password123")
    response = client.post(f"/api/users/{admin.id}/password", json={"new_password": "hacked1234"}, headers=headers)
    assert response.status_code == 403


def test_admin_reset_password_unknown_user_404(client: TestClient, admin: User) -> None:
    headers = auth_headers(client, admin.username, "password123")
    response = client.post(
        "/api/users/00000000-0000-0000-0000-000000000000/password", json={"new_password": "resetbyadmin1"}, headers=headers
    )
    assert response.status_code == 404
