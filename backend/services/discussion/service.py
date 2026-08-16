# 讨论业务：创建 / 查询 / 启动多轮编排 / 消息列表 / 用户介入
# 关键操作同时写入 audit_events，便于管理后台追溯和合规审计。

import asyncio
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_engine.discussion.multi_orchestrator import AgentSpec, run_multi_discussion
from agent_engine.llm import get_chat_llm
from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
from backend.services.audit import AuditRepository
from backend.services.character.repository import CharacterRepository
from backend.services.discussion.repository import DiscussionRepository
from backend.services.discussion.schemas import (
    AgentInfo,
    DiscussionCreateRequest,
    DiscussionResponse,
    MessageResponse,
    TopicGenerateResponse,
)
from backend.services.realtime.publisher import publish_discussion_event
from backend.services.user.repository import UserRepository

# LLM 失败或超时后用静态主题池兜底，保证前端「换一个」始终有结果
DEFAULT_TOPICS = [
    "创新与执行哪个更重要",
    "长期主义是否适合所有创业者",
    "AI 会取代哪些知识工作",
    "开源与商业化如何平衡",
    "远程办公是否提高创造力",
    "第一性原理如何落地到产品决策",
    "增长黑客与品牌建设谁更优先",
    "技术债应该何时偿还",
]


class DiscussionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DiscussionRepository(session)
        self.char_repo = CharacterRepository(session)
        self.audit = AuditRepository(session)

    async def generate_topic(self) -> TopicGenerateResponse:
        """用 LLM 生成约 30 字讨论主题；超时/失败则从静态池随机取一条。

        技术：ChatOpenAI 直调（temperature≈1.0，timeout=8s），不走 deepagent 图。
        """
        import random

        try:
            llm = get_chat_llm(temperature=1.0, timeout=8)
            prompt = (
                "请生成一个适合多人圆桌讨论的主题，要求：\n"
                "1. 中文，大约 20-35 字\n"
                "2. 有观点张力，便于正反双方发言\n"
                "3. 只输出主题本身，不要引号、编号或解释"
            )
            raw = (await llm.ainvoke(prompt)).content
            topic = (raw if isinstance(raw, str) else str(raw)).strip()
            topic = topic.strip("「」『』\"'").splitlines()[0].strip()
            if 4 <= len(topic) <= 80:
                return TopicGenerateResponse(topic=topic, source="llm")
        except Exception:
            # key 未配置、网络抖动、超时：静默回退
            pass

        return TopicGenerateResponse(
            topic=random.choice(DEFAULT_TOPICS),
            source="fallback",
        )

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
        # 讨论创建是 P1 生命周期事件，记录主题/时长/参与角色，便于后续审计与 token 用量关联
        await self.audit.record(
            event_type="discussion.create",
            level="P1",
            user_id=uid,
            discussion_id=disc.id,
            payload={
                "topic": req.topic,
                "duration": req.duration,
                "character_ids": req.character_ids,
            },
        )
        await self.session.commit()
        agents = await self._get_agent_infos(disc.id)
        return self._to_response(disc, agents)

    async def list_discussions(
        self, owner_id: str, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[DiscussionResponse], int, bool]:
        items, total = await self.repo.list_by_owner(
            uuid.UUID(owner_id), page, page_size, search=search
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

        specs = await self._build_specs(disc.id)
        if not specs:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND, "No valid skills")

        await self.repo.update_status(disc, "starting")
        # 启动编排是 P1 生命周期事件，关联 discussion_id 方便后续按讨论查审计
        await self.audit.record(
            event_type="discussion.start",
            level="P1",
            user_id=owner_id,
            discussion_id=disc.id,
            payload={"topic": disc.topic, "duration": disc.duration},
        )
        await self.session.commit()

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

    async def resume_discussion(
        self, owner_id: str, discussion_id: str
    ) -> DiscussionResponse:
        # 续聊：允许已结束或报错的讨论重新启动，保留历史消息作为上下文
        disc = await self.repo.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        if str(disc.owner_id) != owner_id:
            raise BusinessException(ErrorCode.FORBIDDEN, "Not your discussion")
        if disc.status not in ("completed", "error"):
            raise BusinessException(
                ErrorCode.DISCUSSION_INVALID_STATUS,
                f"Discussion status is {disc.status}, expected completed or error",
            )

        specs = await self._build_specs(disc.id)
        if not specs:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND, "No valid skills")

        await self.repo.update_status(disc, "starting")
        await self.audit.record(
            event_type="discussion.resume",
            level="P1",
            user_id=owner_id,
            discussion_id=disc.id,
            payload={"topic": disc.topic, "duration": disc.duration},
        )
        await self.session.commit()
        asyncio.create_task(
            run_multi_discussion(
                discussion_id=disc.id,
                topic=disc.topic,
                duration=disc.duration,
                agents=specs,
                resume=True,
            )
        )

        disc = await self.repo.find_by_id(disc.id)
        agents = await self._get_agent_infos(disc.id)
        return self._to_response(disc, agents)

    async def _build_specs(self, disc_id: uuid.UUID) -> list[AgentSpec]:
        # 根据 discussion_agents 表拼装 AgentSpec；技能被删则跳过
        agents_rows = await self.repo.get_agents(disc_id)
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
        return specs

    async def list_messages(self, discussion_id: str) -> list[MessageResponse]:
        disc = await self.repo.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        rows = await self.repo.list_messages(disc.id)
        return [DiscussionService._msg_to_response(m) for m in rows]

    async def list_messages_after(
        self, discussion_id: str, after: str
    ) -> list[MessageResponse]:
        # SSE 重连追赶：业务入口，解析 ISO 时间戳并调用 repository
        disc = await self.repo.find_by_id(uuid.UUID(discussion_id))
        if not disc:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        from datetime import datetime

        after_dt = datetime.fromisoformat(after)
        rows = await self.repo.list_messages_after(disc.id, after_dt)
        return [DiscussionService._msg_to_response(m) for m in rows]

    @staticmethod
    def _msg_to_response(m) -> MessageResponse:
        return MessageResponse(
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
        # 用户介入属于 P2 内容变更事件，记录谁说了什么，便于后续内容安全审计
        await self.audit.record(
            event_type="user_intervened",
            level="P2",
            user_id=user_id,
            discussion_id=disc.id,
            payload={"round_number": round_number, "content_preview": content[:200]},
        )
        await self.session.commit()
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
        # 讨论删除是 P1 生命周期事件，记录主题和删除者
        await self.audit.record(
            event_type="discussion.delete",
            level="P1",
            user_id=user_id,
            discussion_id=disc.id,
            payload={"topic": disc.topic},
        )
        await self.session.commit()

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
