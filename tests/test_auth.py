import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_customer(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SecurePassword123!",
            "phone": "+8801711112222",
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["email"] == "jane@example.com"
    assert data["role"] == "customer"
    assert "public_id" in data


@pytest.mark.asyncio
async def test_login_and_me(client: AsyncClient):
    # 1. Register
    await client.post(
        "/auth/register",
        json={
            "name": "Auth User",
            "email": "auth_user@example.com",
            "password": "Password123!",
        },
    )

    # 2. Login
    login_res = await client.post(
        "/auth/login",
        json={"email": "auth_user@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()["data"]
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    # 3. /auth/me
    me_res = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == "auth_user@example.com"

    # 4. /auth/refresh
    refresh_res = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()["data"]

    # 5. /auth/logout
    logout_res = await client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_res.status_code == 200

    # Old access token is now blacklisted
    revoked_res = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert revoked_res.status_code == 401
    assert revoked_res.json()["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_rbac_enforcement(client: AsyncClient, customer_auth, admin_auth):
    customer_user, customer_headers = customer_auth
    admin_user, admin_headers = admin_auth

    # Customer accessing admin route should fail with 403
    forbidden_res = await client.get("/admin/users", headers=customer_headers)
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["code"] == "ADMIN_REQUIRED"

    # Admin accessing admin route succeeds
    admin_res = await client.get("/admin/users", headers=admin_headers)
    assert admin_res.status_code == 200
