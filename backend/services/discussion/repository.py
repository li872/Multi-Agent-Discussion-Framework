# 讨论相关的数据库读写

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.discussion import Discussion
from backend.models.discussion_agent import DiscussionAgent


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
        self, owner_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Discussion], int]:
        base = select(Discussion).where(
            Discussion.deleted_at.is_(None),
            Discussion.owner_id == owner_id,
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

    async def get_agents(self, discussion_id: uuid.UUID) -> list[DiscussionAgent]:
        stmt = select(DiscussionAgent).where(
            DiscussionAgent.deleted_at.is_(None),
            DiscussionAgent.discussion_id == discussion_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())