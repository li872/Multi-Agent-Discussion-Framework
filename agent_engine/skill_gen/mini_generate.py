# 学习版角色生成：单次 LLM 调用写 SKILL.md
# 技术：ChatOpenAI.ainvoke + SkillFileManager 写磁盘 + Repository 改 status
#
# 为何单独开 DB session？
# create_task 后台跑时，请求里的 session 往往已关闭；必须用 async_session_factory 新建会话。

from __future__ import annotations

import logging
import uuid

from agent_engine.llm import get_chat_llm
from backend.deps import async_session_factory
from backend.services.audit import AuditRepository
from backend.services.character.file_manager import SkillFileManager
from backend.services.character.repository import CharacterRepository

logger = logging.getLogger(__name__)


async def run_mini_skill_generation(
    skill_id: uuid.UUID,
    owner_id: str,
    skill_name: str,
    display_name: str,
    description: str,
) -> None:
    fm = SkillFileManager()
    llm = get_chat_llm(temperature=0.7, timeout=90)

    prompt = (
        f"请为历史/公众人物「{display_name}」写一份角色扮演用的 SKILL.md。\n"
        f"补充说明：{description or '无'}\n\n"
        f"要求：\n"
        f"1. 用中文 Markdown\n"
        f"2. 第一行标题：# {display_name}\n"
        f"3. 至少包含：一句引用（> 开头）、人物简介、说话风格、核心观点、禁止事项\n"
        f"4. 以「你就是{display_name}本人」的口吻写指导，不要写“作为AI”\n"
        f"5. 全文 600-1200 字\n"
        f"只输出 Markdown 正文，不要用代码围栏包裹。"
    )

    try:
        # 非流式一次拿完整 Markdown（生成质量优先；进度 SSE 以后再加）
        raw = (await llm.ainvoke(prompt)).content
        content = (raw if isinstance(raw, str) else str(raw)).strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("markdown"):
                content = content[len("markdown") :].lstrip()

        await fm.write_file(f"{owner_id}/{skill_name}", "SKILL.md", content)

        # 用第一条引用语当列表页 description（和原项目思路类似）
        quote = ""
        for line in content.splitlines():
            if line.strip().startswith(">"):
                quote = line.strip().lstrip(">").strip()
                break

        async with async_session_factory() as session:
            repo = CharacterRepository(session)
            audit = AuditRepository(session)
            skill = await repo.find_by_id(skill_id)
            if not skill:
                return
            await audit.record(
                event_type="skill.generate_complete",
                level="P1",
                user_id=owner_id,
                payload={
                    "skill_id": str(skill_id),
                    "skill_name": skill_name,
                    "source": "mini_llm",
                },
            )
            await repo.update(
                skill,
                status="ready",
                description=quote or description or f"{display_name} 的角色技能",
            )
    except Exception as exc:
        logger.exception("mini skill generation failed: %s", skill_id)
        async with async_session_factory() as session:
            repo = CharacterRepository(session)
            audit = AuditRepository(session)
            skill = await repo.find_by_id(skill_id)
            if skill:
                await audit.record(
                    event_type="skill.generate_error",
                    level="P1",
                    user_id=owner_id,
                    payload={
                        "skill_id": str(skill_id),
                        "skill_name": skill_name,
                        "error": str(exc),
                    },
                )
                await repo.update(skill, status="error")
