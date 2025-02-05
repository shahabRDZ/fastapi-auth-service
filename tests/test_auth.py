"""Integration tests for /api/v1/auth endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"

VALID_USER = {
    "email": "alice@example.com",
    "username": "alice",
    "password": "Str0ngPass!",
    "full_name": "Alice Example",
}


# ── Registration ───────────────────────────────────────────────────────────────

async def test_register_success(client: AsyncClient) -> None:
    response = await client.post(REGISTER_URL, json=VALID_USER)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == VALID_USER["email"]
    assert data["username"] == VALID_USER["username"]
    assert "hashed_password" not in data
    assert "id" in data


async def test_register_duplicate_email(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=VALID_USER)
    duplicate = {**VALID_USER, "username": "alice2"}
    response = await client.post(REGISTER_URL, json=duplicate)
    assert response.status_code == 409
    assert "email" in response.json()["detail"]


async def test_register_duplicate_username(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=VALID_USER)
    duplicate = {**VALID_USER, "email": "other@example.com"}
    response = await client.post(REGISTER_URL, json=duplicate)
    assert response.status_code == 409
    assert "username" in response.json()["detail"]


async def test_register_weak_password(client: AsyncClient) -> None:
    payload = {**VALID_USER, "email": "weak@example.com", "username": "weakuser", "password": "short"}
    response = await client.post(REGISTER_URL, json=payload)
    assert response.status_code == 422


async def test_register_invalid_email(client: AsyncClient) -> None:
    payload = {**VALID_USER, "email": "not-an-email", "username": "noone"}
    response = await client.post(REGISTER_URL, json=payload)
    assert response.status_code == 422


# ── Login ──────────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(
        LOGIN_URL,
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=VALID_USER)
    response = await client.post(
        LOGIN_URL,
        json={"email": VALID_USER["email"], "password": "WrongPass1"},
    )
    assert response.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    response = await client.post(
        LOGIN_URL,
        json={"email": "ghost@example.com", "password": "SomePass1"},
    )
    assert response.status_code == 401


# ── /me ────────────────────────────────────────────────────────────────────────

async def _get_token(client: AsyncClient) -> str:
    await client.post(REGISTER_URL, json=VALID_USER)
    resp = await client.post(
        LOGIN_URL,
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )
    return resp.json()["access_token"]


async def test_me_authenticated(client: AsyncClient) -> None:
    token = await _get_token(client)
    response = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == VALID_USER["email"]


async def test_me_unauthenticated(client: AsyncClient) -> None:
    response = await client.get(ME_URL)
    assert response.status_code == 403


async def test_me_invalid_token(client: AsyncClient) -> None:
    response = await client.get(ME_URL, headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401


# ── Token refresh ──────────────────────────────────────────────────────────────

async def test_refresh_token_success(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=VALID_USER)
    login_resp = await client.post(
        LOGIN_URL,
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    response = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_refresh_token_invalid(client: AsyncClient) -> None:
    response = await client.post(REFRESH_URL, json={"refresh_token": "bad.token"})
    assert response.status_code == 401


# ── Logout ─────────────────────────────────────────────────────────────────────

async def test_logout(client: AsyncClient) -> None:
    token = await _get_token(client)
    response = await client.post(LOGOUT_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out."
