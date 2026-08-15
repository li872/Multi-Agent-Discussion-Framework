# 讨论业务：创建 / 查询 / 启动多轮编排 / 消息列表 / 用户介入

import asyncio
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_engine.discussion.multi_orchestrator import AgentSpec, run_multi_discussion
from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
from backend.services.character.repository import CharacterRepository
from backend.services.discussion.repository import DiscussionRepository
from backend.services.discussion.schemas import (
    AgentInfo,
    DiscussionCreateRequest,
    DiscussionResponse,
    MessageResponse,
)
from backend.services.realtime.publisher import publish_discussion_event
from backend.services.user.repository import UserRepository


class DiscussionService:
    def __init__(self, session: AsyncSession):
        self.repo = DiscussionRepository(session)
        self.char_repo = CharacterRepository(session)

    async def create_discussion(
        self, owner_id: str, req: DiscussionCreateRequest
    ) -> DiscussionResponse:
        uid = uuid.UUID(owner_id)
        skill_ids = [uuid.UUID(sid) for sid in req.character_ids]

        for sid in skill_ids:
            skill = await self.char_repo.find_by_id(sid)
            if not skill or skill.status != "ready":
                raise BusinessException(
                    ErrorCode.SKILL_NOT_FOUND,
                    f"Skill {sid} not found or not ready",
                )
            if str(skill.owner_id) != owner_id:
                raise BusinessException(
                    ErrorCode.FORBIDDEN,
                    f"Skill '{skill.name}' does not belong to you",
                )

        disc = await self.repo.create_discussion(uid, req.topic, req.duration)
        await self.repo.add_agents(disc.id, skill_ids)
        agents = await self._get_agent_infos(disc.id)
        return self._to_response(disc, agents)

    async def list_discussions(
        self, owner_id: str, page: int, page_size: int
    ) -> tuple[list[DiscussionResponse], int, bool]:
        items, total = await self.repo.list_by_owner(
            uuid.UUID(owner_id), page, page_size
        )
        result = []
        for disc in items:
            agents = await self._get_agent_infos(disc.id)
            result.append(self._to_response(disc, agents))
        has_more = (page * page_size) < total
        return result, total, has_more

    async def get_discussion(self, discussion_id: str) -> DiscussionResponse:
        disc = await self.repo.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        agents = await self._get_agent_infos(disc.id)
        return self._to_response(disc, agents)

    async def start_discussion(
        self, owner_id: str, discussion_id: str
    ) -> DiscussionResponse:
        disc = await self.repo.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        if str(disc.owner_id) != owner_id:
            raise BusinessException(ErrorCode.FORBIDDEN, "Not your discussion")
        if disc.status != "pending":
            raise BusinessException(
                ErrorCode.DISCUSSION_INVALID_STATUS,
                f"Discussion status is {disc.status}, expected pending",
            )

        agents_rows = await self.repo.get_agents(disc.id)
        if not agents_rows:
            raise BusinessException(ErrorCode.INVALID_PARAMS, "No agents")

        specs: list[AgentSpec] = []
        for row in agents_rows:
            skill = await self.char_repo.find_by_id(row.skill_id)
            if not skill:
                continue
            specs.append(
                AgentSpec(
                    agent_id=skill.id,
                    agent_name=skill.name.replace("-perspective", ""),
                    skill_file_path=skill.file_path,
                )
            )
        if not specs:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND, "No valid skills")

        await self.repo.update_status(disc, "starting")

        asyncio.create_task(
            run_multi_discussion(
                discussion_id=disc.id,
                topic=disc.topic,
                duration=disc.duration,
                agents=specs,
            )
        )

        disc = await self.repo.find_by_id(disc.id)
        agents = await self._get_agent_infos(disc.id)
        return self._to_response(disc, agents)

    async def list_messages(self, discussion_id: str) -> list[MessageResponse]:
        disc = await self.repo.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        rows = await self.repo.list_messages(disc.id)
        return [
            MessageResponse(
                id=str(m.id),
                discussion_id=str(m.discussion_id),
                round_number=m.round_number,
                agent_id=str(m.agent_id) if m.agent_id else None,
                agent_name=m.agent_name,
                message_type=m.message_type,
                content=m.content,
                confidence=m.confidence,
                created_at=m.created_at.isoformat(),
            )
            for m in rows
        ]

    async def intervene(
        self, discussion_id: str, user_id: str, content: str
    ) -> MessageResponse:
        disc = await self.repo.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        if str(disc.owner_id) != user_id:
            raise BusinessException(
                ErrorCode.FORBIDDEN, "Cannot intervene in another user's discussion"
            )
        if disc.status not in ("starting", "running"):
            raise BusinessException(
                ErrorCode.DISCUSSION_ENDED,
                f"Discussion status is {disc.status}, cannot intervene",
            )

        user_repo = UserRepository(self.repo.session)
        user = await user_repo.find_by_id(uuid.UUID(user_id))
        username = user.username if user else "观众"

        existing = await self.repo.list_messages(disc.id)
        round_number = existing[-1].round_number if existing else 0

        msg = await self.repo.add_message(
            disc.id,
            round_number=round_number,
            message_type="user_intervene",
            content=content.strip(),
            agent_name=username,
        )
        await publish_discussion_event(
            str(disc.id),
            "message",
            {
                "id": str(msg.id),
                "discussion_id": str(msg.discussion_id),
                "round_number": msg.round_number,
                "agent_id": None,
                "agent_name": msg.agent_name,
                "message_type": msg.message_type,
                "content": msg.content,
                "confidence": None,
                "created_at": msg.created_at.isoformat() if msg.created_at else "",
            },
        )
        return MessageResponse(
            id=str(msg.id),
            discussion_id=str(msg.discussion_id),
            round_number=msg.round_number,
            agent_id=None,
            agent_name=msg.agent_name,
            message_type=msg.message_type,
            content=msg.content,
            confidence=None,
            created_at=msg.created_at.isoformat(),
        )

    async def delete_discussion(self, discussion_id: str, user_id: str) -> None:
        disc = await self.repo.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        if str(disc.owner_id) != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN, "Not your discussion")
        await self.repo.soft_delete(disc)

    async def _get_agent_infos(self, discussion_id: uuid.UUID) -> list[AgentInfo]:
        rows = await self.repo.get_agents(discussion_id)
        agents: list[AgentInfo] = []
        for row in rows:
            skill = await self.char_repo.find_by_id(row.skill_id)
            name = (
                skill.name.replace("-perspective", "")
                if skill
                else str(row.skill_id)
            )
            agents.append(AgentInfo(skill_id=str(row.skill_id), name=name))
        return agents

    @staticmethod
    def _to_response(disc, agents: list[AgentInfo]) -> DiscussionResponse:
        return DiscussionResponse(
            id=str(disc.id),
            owner_id=str(disc.owner_id),
            topic=disc.topic,
            duration=disc.duration,
            status=disc.status,
            started_at=disc.started_at.isoformat() if disc.started_at else None,
            ended_at=disc.ended_at.isoformat() if disc.ended_at else None,
            created_at=disc.created_at.isoformat(),
            updated_at=disc.updated_at.isoformat(),
            agents=agents,
        )


async def get_discussion_service(
    db: AsyncSession = Depends(get_db),
) -> DiscussionService:
    return DiscussionService(db)
