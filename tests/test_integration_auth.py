"""L3：注册/登录/鉴权 — 真实 PG。"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_should_register_and_login_and_get_me(asgi_client, unique_name: str):
    password = "secret12"
    reg = await asgi_client.post(
        "/api/v1/auth/register",
        json={"username": unique_name, "password": password},
    )
    assert reg.status_code == 200
    reg_body = reg.json()
    assert reg_body["code"] == 200
    assert reg_body["data"]["user"]["username"] == unique_name
    token = reg_body["data"]["token"]["token"]
    assert token

    bad = await asgi_client.post(
        "/api/v1/auth/login",
        json={"username": unique_name, "password": "wrongpass"},
    )
    assert bad.status_code in (400, 401, 403) or bad.json().get("code") != 200

    login = await asgi_client.post(
        "/api/v1/auth/login",
        json={"username": unique_name, "password": password},
    )
    assert login.status_code == 200
    assert login.json()["code"] == 200
    login_token = login.json()["data"]["token"]["token"]

    me = await asgi_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["username"] == unique_name


@pytest.mark.asyncio
async def test_should_reject_me_without_token(asgi_client):
    res = await asgi_client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_should_reject_invalid_bearer(asgi_client):
    res = await asgi_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_should_reject_duplicate_username(asgi_client, registered_user):
    res = await asgi_client.post(
        "/api/v1/auth/register",
        json={
            "username": registered_user["username"],
            "password": "secret12",
        },
    )
    body = res.json()
    assert body["code"] != 200
