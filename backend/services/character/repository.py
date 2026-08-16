# 操作 skills 表
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessException, ErrorCode
from backend.models.skill import Skill


class CharacterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        owner_id: uuid.UUID,
        name: str,
        description: str,
        file_path: str,
        tags: list[str] | None = None,
        is_public: bool = False,
        status: str = "ready",
    ) -> Skill:
        skill = Skill(
            owner_id=owner_id,
            name=name,
            description=description,
            file_path=file_path,
            tags=tags or [],
            is_public=is_public,
            status=status,
        )
        self.session.add(skill)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.SKILL_NAME_EXISTS)
        await self.session.refresh(skill)
        return skill

    async def find_by_id(self, skill_id: uuid.UUID) -> Skill | None:
        stmt = select(Skill).where(Skill.deleted_at.is_(None), Skill.id == skill_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_owner_and_name(self, owner_id: uuid.UUID, name: str) -> Skill | None:
        stmt = select(Skill).where(
            Skill.deleted_at.is_(None),
            Skill.owner_id == owner_id,
            Skill.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self, owner_id: uuid.UUID, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[Skill], int]:
        base = select(Skill).where(Skill.deleted_at.is_(None), Skill.owner_id == owner_id)
        if search:
            base = base.where(
                or_(Skill.name.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%"))
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            base.order_by(Skill.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_public(
        self, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[Skill], int]:
        # 画廊：只列公开且未删除的角色
        base = select(Skill).where(
            Skill.deleted_at.is_(None),
            Skill.is_public.is_(True),
            Skill.status == "ready",
        )
        if search:
            base = base.where(
                or_(Skill.name.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%"))
            )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            base.order_by(Skill.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_all(
        self, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[Skill], int]:
        base = select(Skill).where(Skill.deleted_at.is_(None))
        if search:
            base = base.where(
                or_(Skill.name.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%"))
            )
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.order_by(Skill.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_active(self) -> int:
        stmt = select(func.count()).select_from(Skill).where(Skill.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one()

    async def update(self, skill: Skill, **kwargs: Any) -> Skill:
        for key, value in kwargs.items():
            if value is not None and hasattr(skill, key):
                setattr(skill, key, value)
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    async def soft_delete(self, skill: Skill) -> None:
        skill.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()