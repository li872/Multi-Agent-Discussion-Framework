"""L3：角色 CRUD + 文件 + 审计事件 — 真实 PG + 本地 skills 目录。"""

from __future__ import annotations

import uuid
import pytest


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_should_create_character_write_files_and_audit(
    asgi_client, registered_user, tmp_path, monkeypatch
):
    import backend.services.character.file_manager as fm_mod

    monkeypatch.setattr(fm_mod, "SKILLS_ROOT", tmp_path)

    name = f"Jobs{uuid.uuid4().hex[:6]}"
    create = await asgi_client.post(
        "/api/v1/characters",
        headers=registered_user["headers"],
        json={
            "name": name,
            "description": "stay hungry",
            "tags": ["tech"],
            "is_public": False,
        },
    )
    assert create.status_code == 200, create.text
    body = create.json()
    assert body["code"] == 200
    skill = body["data"]
    assert skill["status"] == "ready"
    assert "stay hungry" in (skill.get("description") or "")
    skill_id = skill["id"]

    files = await asgi_client.get(
        f"/api/v1/characters/{skill_id}/files",
        headers=registered_user["headers"],
    )
    assert files.status_code == 200
    file_list = files.json()["data"]
    assert any(
        "SKILL.md" in str(f)
        for f in (
            file_list if isinstance(file_list, list) else file_list.get("files", [])
        )
    )

    content = await asgi_client.get(
        f"/api/v1/characters/{skill_id}/files",
        headers=registered_user["headers"],
        params={"path": "SKILL.md"},
    )
    assert content.status_code == 200
    payload = content.json()["data"]
    text = payload if isinstance(payload, str) else payload.get("content", "")
    assert "stay hungry" in text

    disk = tmp_path / registered_user["user_id"] / f"{name}-perspective" / "SKILL.md"
    assert disk.exists()

    from sqlalchemy import select
    from backend.deps import async_session_factory
    from backend.models.audit_event import AuditEvent

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.event_type == "skill.create",
                    AuditEvent.user_id == uuid.UUID(registered_user["user_id"]),
                )
            )
        ).scalars().all()
        assert any(r.payload.get("skill_id") == skill_id for r in rows)
        assert any(r.level == "P2" for r in rows)


@pytest.mark.asyncio
async def test_should_list_own_characters(asgi_client, registered_user, tmp_path, monkeypatch):
    import backend.services.character.file_manager as fm_mod

    monkeypatch.setattr(fm_mod, "SKILLS_ROOT", tmp_path)
    name = f"Ada{uuid.uuid4().hex[:6]}"
    await asgi_client.post(
        "/api/v1/characters",
        headers=registered_user["headers"],
        json={"name": name, "description": "compute"},
    )
    listed = await asgi_client.get(
        "/api/v1/characters",
        headers=registered_user["headers"],
    )
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert any(name in (c["name"] or "") for c in items)
