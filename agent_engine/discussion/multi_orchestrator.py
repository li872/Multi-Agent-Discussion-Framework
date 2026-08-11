# 多轮去中心化编排：每人先决策 JSON，再按 confidence 选出发言人

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
import uuid
from dataclasses import dataclass

from agent_engine.llm import get_chat_llm
from backend.deps import async_session_factory
from backend.models.base import utcnow
from backend.services.character.file_manager import SKILLS_ROOT
from backend.services.discussion.repository import DiscussionRepository

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3  # 学习阶段上限，避免一次烧太多 token


@dataclass
class AgentSpec:
    agent_id: uuid.UUID
    agent_name: str
    skill_file_path: str
    excerpt: str = ""


@dataclass
class Decision:
    agent_id: uuid.UUID
    agent_name: str
    decision: str  # speak | wait
    confidence: float
    reasoning: str


def _read_skill_excerpt(file_path: str, max_chars: int = 2000) -> str:
    skill_md = SKILLS_ROOT / file_path / "SKILL.md"
    if not skill_md.exists():
        return ""
    return skill_md.read_text(encoding="utf-8")[:max_chars]


def _extract_decision(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    raw = m.group(0) if m else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"decision": "wait", "confidence": 0.0, "reasoning": "解析失败"}
    decision = data.get("decision", "wait")
    if decision not in ("speak", "wait"):
        decision = "wait"
    try:
        conf = round(float(data.get("confidence", 0.0)), 2)
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    reasoning = str(data.get("reasoning", ""))[:80]
    return {"decision": decision, "confidence": conf, "reasoning": reasoning}


def _pick_speaker(decisions: list[Decision]) -> tuple[Decision, bool]:
    speakers = [d for d in decisions if d.decision == "speak"]
    if speakers:
        return max(speakers, key=lambda d: d.confidence), False
    return random.choice(decisions), True


def _history_text(messages: list[tuple[str, str]], limit: int = 8) -> str:
    # messages: (name, content)
    recent = messages[-limit:]
    if not recent:
        return "（尚无发言）"
    return "\n".join(f"{name}：{content}" for name, content in recent)


async def run_multi_discussion(
    discussion_id: uuid.UUID,
    topic: str,
    duration: int,
    agents: list[AgentSpec],
) -> None:
    if not agents:
        return

    async with async_session_factory() as session:
        repo = DiscussionRepository(session)
        disc = await repo.find_by_id(discussion_id)
        if not disc:
            return

        try:
            for a in agents:
                a.excerpt = _read_skill_excerpt(a.skill_file_path)

            await repo.update_status(disc, "running", started_at=utcnow())
            host_llm = get_chat_llm(temperature=0.8, timeout=30)
            think_llm = get_chat_llm(temperature=0.3, timeout=20)
            speak_llm = get_chat_llm(temperature=0.8, timeout=30)

            transcript: list[tuple[str, str]] = []

            intro_prompt = (
                f"你是圆桌讨论主持人。请用中文做简短开场（80-150字），"
                f"主题是「{topic}」，邀请在场嘉宾发言。不要提AI。"
            )
            intro = (await host_llm.ainvoke(intro_prompt)).content
            intro_text = (intro if isinstance(intro, str) else str(intro)).strip()
            await repo.add_message(
                discussion_id,
                round_number=0,
                message_type="host_intro",
                content=intro_text,
                agent_name="主持人",
            )
            transcript.append(("主持人", intro_text))

            started = time.time()
            round_num = 0

            while round_num < MAX_ROUNDS and (time.time() - started) < duration:
                round_num += 1
                history = _history_text(transcript)

                async def _think_one(agent: AgentSpec) -> Decision:
                    prompt = (
                        f"你就是{agent.agent_name}本人，正在参加圆桌讨论。\n"
                        f"主题：{topic}\n"
                        f"人设节选：\n{agent.excerpt}\n\n"
                        f"当前讨论记录：\n{history}\n\n"
                        f"请判断这一轮要不要发言。只输出 JSON，不要其他文字：\n"
                        f'{{"decision":"speak"|"wait","confidence":0.00到1.00两位小数,"reasoning":"10字内理由"}}'
                    )
                    try:
                        raw = (await think_llm.ainvoke(prompt)).content
                        raw_text = raw if isinstance(raw, str) else str(raw)
                        parsed = _extract_decision(raw_text)
                    except Exception:
                        logger.exception("think failed: %s", agent.agent_name)
                        parsed = {
                            "decision": "wait",
                            "confidence": 0.0,
                            "reasoning": "思考失败",
                        }
                    return Decision(
                        agent_id=agent.agent_id,
                        agent_name=agent.agent_name,
                        decision=parsed["decision"],
                        confidence=parsed["confidence"],
                        reasoning=parsed["reasoning"],
                    )

                decisions = list(
                    await asyncio.gather(*[_think_one(a) for a in agents])
                )

                for d in decisions:
                    await repo.add_message(
                        discussion_id,
                        round_number=round_num,
                        message_type="agent_think",
                        content=(
                            f"decision={d.decision}, confidence={d.confidence}, "
                            f"reasoning={d.reasoning}"
                        ),
                        agent_id=d.agent_id,
                        agent_name=d.agent_name,
                        confidence=d.confidence,
                    )

                winner, forced = _pick_speaker(decisions)
                speaker = next(a for a in agents if a.agent_id == winner.agent_id)

                speak_prompt = (
                    f"你就是{speaker.agent_name}本人。\n"
                    f"主题：{topic}\n"
                    f"人设节选：\n{speaker.excerpt}\n\n"
                    f"讨论记录：\n{history}\n\n"
                    f"{'（全员沉默，请你主动打开局面）' if forced else ''}"
                    f"请用中文发言（120-220字）。不要提AI，不要说自己在扮演。"
                )
                speech = (await speak_llm.ainvoke(speak_prompt)).content
                speech_text = (speech if isinstance(speech, str) else str(speech)).strip()
                await repo.add_message(
                    discussion_id,
                    round_number=round_num,
                    message_type="agent_speak",
                    content=speech_text,
                    agent_id=speaker.agent_id,
                    agent_name=speaker.agent_name,
                    confidence=winner.confidence,
                )
                transcript.append((speaker.agent_name, speech_text))

            summary_prompt = (
                f"你是圆桌主持人。主题「{topic}」。\n"
                f"讨论记录：\n{_history_text(transcript, limit=20)}\n\n"
                f"请用中文做简短总结（80-150字），不要提AI。"
            )
            summary = (await host_llm.ainvoke(summary_prompt)).content
            summary_text = (summary if isinstance(summary, str) else str(summary)).strip()
            await repo.add_message(
                discussion_id,
                round_number=round_num + 1,
                message_type="host_summary",
                content=summary_text,
                agent_name="主持人",
            )

            disc = await repo.find_by_id(discussion_id)
            if disc:
                await repo.update_status(disc, "completed", ended_at=utcnow())
        except Exception:
            logger.exception("multi discussion failed: %s", discussion_id)
            disc = await repo.find_by_id(discussion_id)
            if disc:
                await repo.update_status(disc, "error", ended_at=utcnow())