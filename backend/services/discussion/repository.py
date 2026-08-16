# 讨论相关的数据库读写

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.discussion import Discussion
from backend.models.discussion_agent import DiscussionAgent
from backend.models.discussion_message import DiscussionMessage


class DiscussionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_discussion(
        self, owner_id: uuid.UUID, topic: str, duration: int
    ) -> Discussion:
        disc = Discussion(
            owner_id=owner_id,
            topic=topic,
            duration=duration,
            status="pending",
        )
        self.session.add(disc)
        await self.session.commit()
        await self.session.refresh(disc)
        return disc

    async def add_agents(
        self, discussion_id: uuid.UUID, skill_ids: list[uuid.UUID]
    ) -> None:
        for sid in skill_ids:
            self.session.add(
                DiscussionAgent(discussion_id=discussion_id, skill_id=sid)
            )
        await self.session.commit()

    async def find_by_id(self, discussion_id: uuid.UUID) -> Discussion | None:
        stmt = select(Discussion).where(
            Discussion.deleted_at.is_(None),
            Discussion.id == discussion_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self, owner_id: uuid.UUID, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[Discussion], int]:
        # 讨论列表：支持按 topic 模糊搜索（前端搜索框用）
        base = select(Discussion).where(
            Discussion.deleted_at.is_(None),
            Discussion.owner_id == owner_id,
        )
        if search:
            base = base.where(
                or_(
                    Discussion.topic.ilike(f"%{search}%"),
                    Discussion.status.ilike(f"%{search}%"),
                )
            )
        total = (
            await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        stmt = (
            base.order_by(Discussion.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_all(
        self, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[Discussion], int]:
        base = select(Discussion).where(Discussion.deleted_at.is_(None))
        if search:
            base = base.where(
                or_(
                    Discussion.topic.ilike(f"%{search}%"),
                    Discussion.status.ilike(f"%{search}%"),
                )
            )
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.order_by(Discussion.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_orphans(self) -> list[Discussion]:
        from backend.models.base import utcnow

        now = utcnow()
        stmt = select(Discussion).where(
            Discussion.deleted_at.is_(None),
            Discussion.status.in_(("starting", "running")),
            Discussion.started_at.is_not(None),
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        out: list[Discussion] = []
        for d in rows:
            deadline = d.started_at.timestamp() + int(d.duration) + 120
            if deadline < now.timestamp():
                out.append(d)
        return out

    async def count_active(self) -> int:
        stmt = select(func.count()).select_from(Discussion).where(
            Discussion.deleted_at.is_(None)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def get_agents(self, discussion_id: uuid.UUID) -> list[DiscussionAgent]:
        stmt = select(DiscussionAgent).where(
            DiscussionAgent.deleted_at.is_(None),
            DiscussionAgent.discussion_id == discussion_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, disc: Discussion) -> None:
        # 软删除：列表/详情不再出现；消息仍留在库里便于审计（一期不做级联清消息）
        from backend.models.base import utcnow

        disc.deleted_at = utcnow()
        await self.session.commit()

    async def update_status(
        self,
        disc: Discussion,
        status: str,
        *,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> Discussion:
        disc.status = status
        if started_at is not None:
            disc.started_at = started_at
        if ended_at is not None:
            disc.ended_at = ended_at
        await self.session.commit()
        await self.session.refresh(disc)
        return disc

    async def add_message(
        self,
        discussion_id: uuid.UUID,
        *,
        round_number: int,
        message_type: str,
        content: str,
        agent_id: uuid.UUID | None = None,
        agent_name: str | None = None,
        confidence: float | None = None,
    ) -> DiscussionMessage:
        msg = DiscussionMessage(
            discussion_id=discussion_id,
            round_number=round_number,
            message_type=message_type,
            content=content,
            agent_id=agent_id,
            agent_name=agent_name,
            confidence=confidence,
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def list_messages(
        self, discussion_id: uuid.UUID
    ) -> list[DiscussionMessage]:
        stmt = (
            select(DiscussionMessage)
            .where(
                DiscussionMessage.deleted_at.is_(None),
                DiscussionMessage.discussion_id == discussion_id,
            )
            .order_by(
                DiscussionMessage.round_number.asc(),
                DiscussionMessage.created_at.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_messages_after(
        self, discussion_id: uuid.UUID, after: datetime
    ) -> int:
        stmt = select(func.count()).select_from(DiscussionMessage).where(
            DiscussionMessage.deleted_at.is_(None),
            DiscussionMessage.discussion_id == discussion_id,
            DiscussionMessage.created_at > after,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_messages_after(
        self,
        discussion_id: uuid.UUID,
        after: datetime,
        *,
        limit: int | None = None,
        offset: int = 0,
        newest_first: bool = False,
    ) -> list[DiscussionMessage]:
        order = (
            DiscussionMessage.created_at.desc()
            if newest_first
            else DiscussionMessage.created_at.asc()
        )
        stmt = (
            select(DiscussionMessage)
            .where(
                DiscussionMessage.deleted_at.is_(None),
                DiscussionMessage.discussion_id == discussion_id,
                DiscussionMessage.created_at > after,
            )
            .order_by(order)
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        if newest_first:
            rows.reverse()
        return rows