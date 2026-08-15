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
from backend.models.discussion_message import DiscussionMessage
from backend.services.character.file_manager import SKILLS_ROOT
from backend.services.discussion.repository import DiscussionRepository
from backend.services.realtime.publisher import publish_discussion_event

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3  # 学习阶段上限，避免一次烧太多 token


async def _publish_message(discussion_id: uuid.UUID, msg: DiscussionMessage) -> None:
    await publish_discussion_event(
        str(discussion_id),
        "message",
        {
            "id": str(msg.id),
            "discussion_id": str(msg.discussion_id),
            "round_number": msg.round_number,
            "agent_id": str(msg.agent_id) if msg.agent_id else None,
            "agent_name": msg.agent_name,
            "message_type": msg.message_type,
            "content": msg.content,
            "confidence": msg.confidence,
            "created_at": msg.created_at.isoformat() if msg.created_at else "",
        },
    )


async def _publish_status(discussion_id: uuid.UUID, status: str) -> None:
    await publish_discussion_event(
        str(discussion_id),
        "status",
        {"status": status},
    )


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
            await _publish_status(discussion_id, "running")
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
            intro_msg = await repo.add_message(
                discussion_id,
                round_number=0,
                message_type="host_intro",
                content=intro_text,
                agent_name="主持人",
            )
            await _publish_message(discussion_id, intro_msg)
            transcript.append(("主持人", intro_text))

            started = time.time()
            round_num = 0

            while round_num < MAX_ROUNDS and (time.time() - started) < duration:
                round_num += 1
                # 每轮开始前从 PG 重建上下文，这样用户介入能进入下一轮
                db_msgs = await repo.list_messages(discussion_id)
                transcript = []
                for m in db_msgs:
                    if m.message_type not in (
                        "host_intro",
                        "agent_speak",
                        "user_intervene",
                    ):
                        continue
                    label = m.agent_name or "未知"
                    if m.message_type == "user_intervene":
                        label = f"观众（{label}）"
                    transcript.append((label, m.content))
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
                    think_msg = await repo.add_message(
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
                    await _publish_message(discussion_id, think_msg)

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



                # --- 发言真流式（重难点）---
                # 技术：LangChain ChatOpenAI.astream + Redis Pub/Sub + SSE
                # 作用：边生成边推 chunk，前端可打字机显示；结束后再整段写入 PostgreSQL
                await publish_discussion_event(
                    str(discussion_id),
                    "agent_speak_start",
                    {
                        "agent_id": str(speaker.agent_id),
                        "agent_name": speaker.agent_name,
                        "round": round_num,
                        # temp_id：前端临时气泡的主键，入库前还没有真实 message UUID
                        "temp_id": f"stream-{round_num}-{speaker.agent_id}",
                    },
                )

                parts: list[str] = []
                # astream：异步迭代模型输出的增量文本（每包常是若干 token，代码里叫 chunk）
                async for chunk in speak_llm.astream(speak_prompt):
                    piece = chunk.content
                    text = piece if isinstance(piece, str) else str(piece or "")
                    if not text:
                        continue
                    parts.append(text)
                    await publish_discussion_event(
                        str(discussion_id),
                        "agent_speak_chunk",
                        {
                            "temp_id": f"stream-{round_num}-{speaker.agent_id}",
                            "agent_name": speaker.agent_name,
                            "content": text,
                        },
                    )

                speech_text = "".join(parts).strip()
                # 落库：PostgreSQL 仍存完整发言（权威数据）；再推正式 message 事件
                speak_msg = await repo.add_message(
                    discussion_id,
                    round_number=round_num,
                    message_type="agent_speak",
                    content=speech_text,
                    agent_id=speaker.agent_id,
                    agent_name=speaker.agent_name,
                    confidence=winner.confidence,
                )
                await _publish_message(discussion_id, speak_msg)
                transcript.append((speaker.agent_name, speech_text))

            summary_prompt = (
                f"你是圆桌主持人。主题「{topic}」。\n"
                f"讨论记录：\n{_history_text(transcript, limit=20)}\n\n"
                f"请用中文做简短总结（80-150字），不要提AI。"
            )
            summary = (await host_llm.ainvoke(summary_prompt)).content
            summary_text = (summary if isinstance(summary, str) else str(summary)).strip()
            summary_msg = await repo.add_message(
                discussion_id,
                round_number=round_num + 1,
                message_type="host_summary",
                content=summary_text,
                agent_name="主持人",
            )
            await _publish_message(discussion_id, summary_msg)

            disc = await repo.find_by_id(discussion_id)
            if disc:
                await repo.update_status(disc, "completed", ended_at=utcnow())
            await _publish_status(discussion_id, "completed")
        except Exception:
            logger.exception("multi discussion failed: %s", discussion_id)
            disc = await repo.find_by_id(discussion_id)
            if disc:
                await repo.update_status(disc, "error", ended_at=utcnow())
            await _publish_status(discussion_id, "error")