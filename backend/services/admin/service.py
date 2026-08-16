# 管理后台业务：用户/角色/讨论运维 + 统计 + 审计事件
from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from backend.deps import get_db
from backend.models.base import utcnow
from backend.services.audit import AuditRepository
from backend.services.audit.repository import AuditEvent
from backend.services.character.repository import CharacterRepository
from backend.services.discussion.repository import DiscussionRepository
from backend.services.user.repository import UserRepository


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = AuditRepository(session)
        self.users = UserRepository(session)
        self.characters = CharacterRepository(session)
        self.discussions = DiscussionRepository(session)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def list_audit_events(
        self,
        *,
        user_id: str | uuid.UUID | None = None,
        discussion_id: str | uuid.UUID | None = None,
        event_type: str | None = None,
        level: str | None = None,
        after_id: str | uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[AuditEvent], int]:
        items = await self.audit.list_events(
            user_id=user_id,
            discussion_id=discussion_id,
            event_type=event_type,
            level=level,
            after_id=after_id,
            limit=limit,
            offset=offset,
        )
        total = await self.audit.count_events(
            user_id=user_id,
            discussion_id=discussion_id,
            event_type=event_type,
            level=level,
        )
        return items, total

    async def stats_overview(self) -> dict:
        return {
            "users": await self.users.count_all(),
            "characters": await self.characters.count_active(),
            "discussions": await self.discussions.count_active(),
        }

    def _page(self, items, total: int, page: int, page_size: int) -> dict:
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    async def list_users(self, page: int, page_size: int, search: str | None) -> dict:
        rows, total = await self.users.list_all(page, page_size, search)
        items = [
            {
                "id": str(u.id),
                "username": u.username,
                "phone": u.phone,
                "status": "disabled" if u.deleted_at else "enabled",
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ]
        return self._page(items, total, page, page_size)

    async def get_user(self, user_id: str) -> dict:
        user = await self.users.find_by_id_any(uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {
            "id": str(user.id),
            "username": user.username,
            "phone": user.phone,
            "status": "disabled" if user.deleted_at else "enabled",
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    async def set_user_status(self, user_id: str, enabled: bool) -> dict:
        user = await self.users.find_by_id_any(uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.deleted_at = None if enabled else utcnow()
        await self.users.update(user)
        await self.audit.record(
            event_type="user.status_changed",
            level="P0",
            user_id=user.id,
            payload={"status": "enabled" if enabled else "disabled"},
        )
        await self.session.commit()
        return await self.get_user(user_id)

    async def reset_password(self, user_id: str, password: str) -> dict:
        user = await self.users.find_by_id_any(uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.password_hash = self.pwd_context.hash(password)
        await self.users.update(user)
        await self.audit.record(
            event_type="user.password_reset",
            level="P0",
            user_id=user.id,
            payload={"username": user.username},
        )
        await self.session.commit()
        return {"id": str(user.id), "ok": True}

    async def list_characters(self, page: int, page_size: int, search: str | None) -> dict:
        rows, total = await self.characters.list_all(page, page_size, search)
        items = [
            {
                "id": str(s.id),
                "owner_id": str(s.owner_id),
                "name": s.name,
                "status": s.status,
                "is_public": s.is_public,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in rows
        ]
        return self._page(items, total, page, page_size)

    async def set_character_visibility(self, skill_id: str, is_public: bool) -> dict:
        skill = await self.characters.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
        await self.characters.update(skill, is_public=is_public)
        await self.audit.record(
            event_type="skill.visibility_changed",
            level="P1",
            payload={"skill_id": skill_id, "is_public": is_public},
        )
        await self.session.commit()
        return {"id": skill_id, "is_public": is_public}

    async def delete_character(self, skill_id: str) -> dict:
        skill = await self.characters.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
        name = skill.name
        await self.characters.soft_delete(skill)
        await self.audit.record(
            event_type="character.deleted_by_admin",
            level="P1",
            payload={"skill_id": skill_id, "skill_name": name},
        )
        await self.session.commit()
        return {"id": skill_id, "ok": True}

    async def list_discussions(self, page: int, page_size: int, search: str | None) -> dict:
        rows, total = await self.discussions.list_all(page, page_size, search)
        items = [
            {
                "id": str(d.id),
                "owner_id": str(d.owner_id),
                "topic": d.topic,
                "status": d.status,
                "duration": d.duration,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in rows
        ]
        return self._page(items, total, page, page_size)

    async def get_discussion(self, discussion_id: str) -> dict:
        disc = await self.discussions.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")
        messages = await self.discussions.list_messages(disc.id)
        return {
            "id": str(disc.id),
            "owner_id": str(disc.owner_id),
            "topic": disc.topic,
            "status": disc.status,
            "duration": disc.duration,
            "created_at": disc.created_at.isoformat() if disc.created_at else None,
            "messages": [
                {
                    "id": str(m.id),
                    "round_number": m.round_number,
                    "agent_name": m.agent_name,
                    "message_type": m.message_type,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }

    async def delete_discussion(self, discussion_id: str) -> dict:
        disc = await self.discussions.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")
        topic = disc.topic
        await self.discussions.soft_delete(disc)
        await self.audit.record(
            event_type="discussion.deleted_by_admin",
            level="P1",
            discussion_id=disc.id,
            payload={"topic": topic},
        )
        await self.session.commit()
        return {"id": discussion_id, "ok": True}


async def get_admin_service(
    db: AsyncSession = Depends(get_db),
) -> AdminService:
    return AdminService(db)
