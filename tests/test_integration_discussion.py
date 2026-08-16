"""L3：讨论创建 + 审计 + Redis 健康 — 真实 PG/Redis；启动编排 mock 掉 LLM。"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
import redis.asyncio as redis

from backend.config import settings


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_should_ping_redis():
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        assert await client.ping() is True
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_should_create_and_start_discussion_with_audit(
    asgi_client, registered_user, tmp_path, monkeypatch
):
    import backend.services.character.file_manager as fm_mod
    import backend.services.discussion.service as disc_mod

    monkeypatch.setattr(fm_mod, "SKILLS_ROOT", tmp_path)
    monkeypatch.setattr(disc_mod, "run_multi_discussion", AsyncMock())

    name = f"Turing{uuid.uuid4().hex[:6]}"
    created = await asgi_client.post(
        "/api/v1/characters",
        headers=registered_user["headers"],
        json={"name": name, "description": "computing machinery"},
    )
    assert created.status_code == 200, created.text
    skill_id = created.json()["data"]["id"]

    topic = f"integration topic {uuid.uuid4().hex[:8]}"
    disc = await asgi_client.post(
        "/api/v1/discussions",
        headers=registered_user["headers"],
        json={
            "topic": topic,
            "character_ids": [skill_id],
            "duration": 60,
        },
    )
    assert disc.status_code == 200, disc.text
    body = disc.json()
    assert body["code"] == 200
    discussion_id = body["data"]["id"]
    assert body["data"]["topic"] == topic
    assert body["data"]["status"] == "pending"

    started = await asgi_client.post(
        f"/api/v1/discussions/{discussion_id}/start",
        headers=registered_user["headers"],
    )
    assert started.status_code == 200, started.text
    assert started.json()["data"]["status"] == "starting"
    disc_mod.run_multi_discussion.assert_called()

    from sqlalchemy import select
    from backend.deps import async_session_factory
    from backend.models.audit_event import AuditEvent

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.discussion_id == uuid.UUID(discussion_id),
                )
            )
        ).scalars().all()
        types = {r.event_type for r in rows}
        assert "discussion.create" in types
        assert "discussion.start" in types
        assert all(r.level == "P1" for r in rows if r.event_type.startswith("discussion."))
        assert any(str(r.user_id) == registered_user["user_id"] for r in rows)


@pytest.mark.asyncio
async def test_should_health_see_db_and_redis(asgi_client):
    res = await asgi_client.get("/api/v1/health/detailed")
    assert res.status_code == 200
    components = res.json()["data"]["components"]
    assert components["database"]["status"] == "healthy"
    assert components["redis"]["status"] == "healthy"
