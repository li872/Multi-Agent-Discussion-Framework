# 轻量 conftest：收集阶段不连 PG / Redis / LLM。
# 集成测试通过 pytest.mark.integration 触发，并依赖真实服务。

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: needs PostgreSQL and Redis")
    config.addinivalue_line("markers", "e2e: browser or live services")
    config.addinivalue_line("markers", "external: real LLM or Tavily")


@pytest.fixture
def unique_name() -> str:
    return f"u_{uuid.uuid4().hex[:10]}"


@pytest.fixture(scope="session")
async def _engine_ready() -> AsyncIterator[None]:
    """集成测试共用一个事件循环；NullPool 避免 asyncpg 连接复用冲突。"""
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("REDIS_HOST", "localhost")

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import backend.deps as deps
    from backend.config import settings

    await deps.async_engine.dispose()
    engine = create_async_engine(settings.db_url, echo=False, poolclass=NullPool)
    deps.async_engine = engine
    deps.async_session_factory = async_sessionmaker(
        engine, class_=deps.AsyncSession, expire_on_commit=False
    )
    yield
    await engine.dispose()


@pytest.fixture
async def asgi_client(_engine_ready) -> AsyncIterator:
    """HTTPX ASGI client against backend.main.app（延迟导入）。"""
    from httpx import ASGITransport, AsyncClient

    from backend.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def registered_user(asgi_client, unique_name: str) -> dict:
    password = "secret12"
    res = await asgi_client.post(
        "/api/v1/auth/register",
        json={"username": unique_name, "password": password, "phone": None},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["code"] == 200
    token = body["data"]["token"]["token"]
    user = body["data"]["user"]
    return {
        "username": unique_name,
        "password": password,
        "token": token,
        "user_id": user["id"],
        "headers": {"Authorization": f"Bearer {token}"},
    }
