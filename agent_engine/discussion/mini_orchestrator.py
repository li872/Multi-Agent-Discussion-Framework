# 最小真编排：host_intro → 首位角色发言 → host_summary（ChatOpenAI，暂不接 deepagents）
# 作用： 真调 LLM：开场 → 一人发言 → 总结，并写进数据库

from __future__ import annotations

import logging
import uuid

from agent_engine.llm import get_chat_llm
from backend.deps import async_session_factory
from backend.models.base import utcnow
from backend.services.character.file_manager import SKILLS_ROOT
from backend.services.discussion.repository import DiscussionRepository

logger = logging.getLogger(__name__)


def _read_skill_excerpt(file_path: str, max_chars: int = 2500) -> str:
    skill_md = SKILLS_ROOT / file_path / "SKILL.md"
    if not skill_md.exists():
        return ""
    text = skill_md.read_text(encoding="utf-8")
    return text[:max_chars]


async def run_mini_discussion(
    discussion_id: uuid.UUID,
    topic: str,
    agent_id: uuid.UUID,
    agent_name: str,
    skill_file_path: str,
) -> None:
    """后台任务：必须自建 DB session，不能复用请求里的 session。"""
    async with async_session_factory() as session:
        repo = DiscussionRepository(session)
        disc = await repo.find_by_id(discussion_id)
        if not disc:
            return

        try:
            await repo.update_status(disc, "running", started_at=utcnow())
            llm = get_chat_llm(temperature=0.8, timeout=30)

            intro_prompt = (
                f"你是圆桌讨论主持人。请用中文做一段简短开场（80-150字），"
                f"介绍主题「{topic}」，邀请嘉宾发言。不要提AI、模型、提示词。"
            )
            intro = (await llm.ainvoke(intro_prompt)).content
            intro_text = intro if isinstance(intro, str) else str(intro)
            await repo.add_message(
                discussion_id,
                round_number=0,
                message_type="host_intro",
                content=intro_text.strip(),
                agent_name="主持人",
            )

            excerpt = _read_skill_excerpt(skill_file_path)
            speak_prompt = (
                f"你就是{agent_name}本人，正在参加圆桌讨论。\n"
                f"主题：{topic}\n"
                f"下面是你的人设资料节选：\n{excerpt}\n\n"
                f"请用中文发表一段观点（120-220字）。"
                f"不要说自己是AI，不要说“作为xxx角色”，直接以本人口吻说话。"
            )
            speech = (await llm.ainvoke(speak_prompt)).content
            speech_text = speech if isinstance(speech, str) else str(speech)
            await repo.add_message(
                discussion_id,
                round_number=1,
                message_type="agent_speak",
                content=speech_text.strip(),
                agent_id=agent_id,
                agent_name=agent_name,
                confidence=0.82,
            )

            summary_prompt = (
                f"你是圆桌主持人。主题是「{topic}」。\n"
                f"开场：{intro_text}\n"
                f"{agent_name}说：{speech_text}\n\n"
                f"请用中文做简短总结（80-150字），不要提AI。"
            )
            summary = (await llm.ainvoke(summary_prompt)).content
            summary_text = summary if isinstance(summary, str) else str(summary)
            await repo.add_message(
                discussion_id,
                round_number=2,
                message_type="host_summary",
                content=summary_text.strip(),
                agent_name="主持人",
            )

            disc = await repo.find_by_id(discussion_id)
            if disc:
                await repo.update_status(disc, "completed", ended_at=utcnow())
        except Exception:
            logger.exception("mini discussion failed: %s", discussion_id)
            disc = await repo.find_by_id(discussion_id)
            if disc:
                await repo.update_status(disc, "error", ended_at=utcnow())