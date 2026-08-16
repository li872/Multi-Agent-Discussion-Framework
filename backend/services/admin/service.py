# 管理后台业务：主后端侧给审计后台代理调用的管理接口。
#
# 当前先把审计事件查询放这里，后续用户管理 / 讨论管理 / 角色管理 / 系统健康等接口也逐步接入。
# 权限：通过 X-Admin-Token 请求头做简单校验，等审计后端搭建后替换为服务 JWT。
from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.deps import get_db
from backend.services.audit import AuditRepository
from backend.services.audit.repository import AuditEvent


class AdminService:
    def __init__(self, session: AsyncSession):
        self.audit = AuditRepository(session)

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
        """按条件分页查询审计事件，返回列表和总数。"""
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


async def get_admin_service(
    db: AsyncSession = Depends(get_db),
) -> AdminService:
    return AdminService(db)
