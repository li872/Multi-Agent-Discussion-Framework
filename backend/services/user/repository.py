# 只负责数据库读写，不管业务规则
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_username(self, username: str) -> User | None:
        stmt = select(User).where(
            User.deleted_at.is_(None),
            User.username == username,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_phone(self, phone: str) -> User | None:
        stmt = select(User).where(
            User.deleted_at.is_(None),
            User.phone == phone,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(
            User.deleted_at.is_(None),
            User.id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_id_any(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[User], int]:
        base = select(User)
        if search:
            base = base.where(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                )
            )
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_all(self) -> int:
        stmt = select(func.count()).select_from(User)
        return (await self.session.execute(stmt)).scalar_one()

    async def create(self, username: str, password_hash: str, phone: str | None) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            phone=phone,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        # 提交已修改的 User 对象；updated_at 由 ORM onupdate 自动维护
        await self.session.commit()
        await self.session.refresh(user)
        return user