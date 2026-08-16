# 业务审计 Repository：只负责 audit_events 表的写入和查询，不包含业务规则。
#
# 技术说明：
# - 写入使用调用方传入的同一个 AsyncSession，不单独 commit；
#   这样审计事件与业务操作共享事务，失败一起回滚。
# - level 只能是 P0/P1/P2，调用方必须显式传入，避免默认 P2 埋没高风险事件。
# - user_id / discussion_id 可以是字符串（来自 JWT 或 URL）或 UUID 对象。

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_event import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_uuid(self, value: str | uuid.UUID | None) -> uuid.UUID | None:
        """把 UUID 字符串或对象统一转成 UUID 对象；None 保持 None。"""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)

    async def record(
        self,
        event_type: str,
        level: str,
        user_id: str | uuid.UUID | None = None,
        discussion_id: str | uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> AuditEvent:
        """记录一条审计事件。注意：只 add 到 session，commit 由调用方负责。"""
        event = AuditEvent(
            event_type=event_type,
            level=level,
            user_id=self._to_uuid(user_id),
            discussion_id=self._to_uuid(discussion_id),
            payload=payload or {},
        )
        self.session.add(event)
        await self.session.flush()  # 生成 id 但暂不提交，等调用方统一 commit
        return event

    async def list_events(
        self,
        *,
        user_id: str | uuid.UUID | None = None,
        discussion_id: str | uuid.UUID | None = None,
        event_type: str | None = None,
        level: str | None = None,
        after_id: str | uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AuditEvent]:
        """按条件分页查询审计事件。"""
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
        if user_id is not None:
            stmt = stmt.where(AuditEvent.user_id == self._to_uuid(user_id))
        if discussion_id is not None:
            stmt = stmt.where(AuditEvent.discussion_id == self._to_uuid(discussion_id))
        if event_type is not None:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if level is not None:
            stmt = stmt.where(AuditEvent.level == level)
        if after_id is not None:
            # 游标分页：只返回 created_at 早于 after_id 对应事件的事件
            after_event = await self._get_by_id(after_id)
            if after_event:
                stmt = stmt.where(AuditEvent.created_at < after_event.created_at)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, event_id: str | uuid.UUID) -> AuditEvent | None:
        return await self._get_by_id(event_id)

    async def _get_by_id(self, event_id: str | uuid.UUID) -> AuditEvent | None:
        stmt = select(AuditEvent).where(AuditEvent.id == self._to_uuid(event_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_events(
        self,
        *,
        user_id: str | uuid.UUID | None = None,
        discussion_id: str | uuid.UUID | None = None,
        event_type: str | None = None,
        level: str | None = None,
    ) -> int:
        """按条件统计审计事件数量。"""
        from sqlalchemy import func

        stmt = select(func.count(AuditEvent.id))
        if user_id is not None:
            stmt = stmt.where(AuditEvent.user_id == self._to_uuid(user_id))
        if discussion_id is not None:
            stmt = stmt.where(AuditEvent.discussion_id == self._to_uuid(discussion_id))
        if event_type is not None:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if level is not None:
            stmt = stmt.where(AuditEvent.level == level)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
