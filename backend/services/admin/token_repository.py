from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.token_usage import TokenUsage


class TokenUsageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def sum_tokens(
        self,
        *,
        user_id: uuid.UUID | None = None,
        discussion_id: uuid.UUID | None = None,
    ) -> int:
        stmt = select(func.coalesce(func.sum(TokenUsage.tokens), 0)).where(
            TokenUsage.deleted_at.is_(None)
        )
        if user_id is not None:
            stmt = stmt.where(TokenUsage.user_id == user_id)
        if discussion_id is not None:
            stmt = stmt.where(TokenUsage.discussion_id == discussion_id)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def trend_days(self, days: int = 7) -> list[dict]:
        start = datetime.now(timezone.utc) - timedelta(days=days)
        day = func.date_trunc("day", TokenUsage.created_at)
        stmt = (
            select(day.label("day"), func.coalesce(func.sum(TokenUsage.tokens), 0))
            .where(TokenUsage.deleted_at.is_(None), TokenUsage.created_at >= start)
            .group_by(day)
            .order_by(day)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {"day": r[0].date().isoformat() if r[0] else None, "tokens": int(r[1])}
            for r in rows
        ]
