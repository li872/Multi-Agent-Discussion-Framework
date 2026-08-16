# 完整 Nuwa Skill 生成管线（后台任务）
# 技术：deepagents.create_deep_agent + Tavily 联网搜索 + LangGraph astream + Redis Pub/Sub
# 作用：把 nuwa-source 的多 Agent 视角蒸馏流程接进 MADF，生成带 references/research/ 的完整 SKILL

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from pathlib import Path

from agent_engine.skill_gen.nvwa_agent.agent import create_nvwa_agent
from backend.deps import async_session_factory
from backend.services.character.file_manager import SKILLS_ROOT
from backend.services.character.repository import CharacterRepository
from backend.services.realtime.publisher import publish_generation_event

logger = logging.getLogger(__name__)

# nuwa-skill 源目录，调用方会把它复制到每个任务的独立工作目录
NUWA_SOURCE = Path(__file__).parent / "nuwa-agent-skill"


def _publish(
    skill_id: uuid.UUID,
    level: str,
    message: str,
    extra: dict | None = None,
) -> None:
    # 异步发布到 Redis；create_task 避免阻塞生成管线的迭代
    payload: dict = {"level": level, "message": message}
    if extra:
        payload.update(extra)
    asyncio.create_task(publish_generation_event(str(skill_id), payload))


async def _copytree_async(src: Path, dst: Path) -> None:
    if dst.exists():
        await asyncio.to_thread(shutil.rmtree, str(dst))
    await asyncio.to_thread(shutil.copytree, str(src), str(dst))


async def _count_files(dir_path: Path) -> int:
    if not dir_path.exists():
        return 0

    def _count() -> int:
        return sum(1 for _ in dir_path.rglob("*") if _.is_file())

    return await asyncio.to_thread(_count)


async def _extract_quote(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return ""
    content = await asyncio.to_thread(skill_md.read_text, encoding="utf-8")
    for line in content.splitlines():
        if line.strip().startswith(">"):
            return line.strip().lstrip(">").strip()
    return ""


async def _handle_event(skill_id: uuid.UUID, event: dict) -> None:
    """解析 astream 事件，把主阶段/子 Agent/工具调用推为进度事件。"""
    if not isinstance(event, dict):
        return
    for node_name, node_data in event.items():
        if node_name in ("__start__", "__end__"):
            continue
        if not isinstance(node_data, dict):
            continue

        messages = node_data.get("messages")
        if not messages:
            continue
        if not isinstance(messages, list):
            messages = [messages]

        for msg in messages:
            if not hasattr(msg, "content"):
                continue
            content = msg.content if isinstance(msg.content, str) else str(msg.content or "")

            # 工具调用：主要关注 internet_search 和子 Agent 派发
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name", "unknown")
                    args = tc.get("args", {}) or {}
                    if name == "internet_search":
                        _publish(
                            skill_id,
                            "tool",
                            f"联网搜索：{args.get('query', '')}",
                            {"tool": name, "query": args.get("query")},
                        )
                    elif name == "task":
                        subagent = args.get("subagent_type") or args.get("agent", "unknown")
                        _publish(
                            skill_id,
                            "sub",
                            f"子智能体：{subagent}",
                            {"agent": subagent},
                        )
                    else:
                        _publish(skill_id, "tool", f"工具调用：{name}", {"tool": name})

            # 主阶段文本（截断避免消息过大）
            if content:
                _publish(skill_id, "main", content[:200], {"node": node_name})


async def run_full_skill_generation(
    skill_id: uuid.UUID,
    owner_id: str,
    skill_name: str,
    display_name: str,
    description: str,
) -> None:
    """
    运行完整 Nuwa Skill 生成管线。

    流程：
    1. 在 .gen_work/{skill_id}/ 下建立独立工作目录，复制 nuwa-agent-skill 源。
    2. 创建 deepagent 并 astream 执行 prompt。
    3. 解析事件并发布生成进度（main / sub / tool / done / error）。
    4. 把产物从 .gen_work/skill-distill/{skill_name}/ 复制到 skills/{owner_id}/{skill_name}/。
    5. 更新 PG skills 表：status=ready、description、source_count。
    """
    work_root = SKILLS_ROOT / ".gen_work" / str(skill_id)
    final_dir = SKILLS_ROOT / owner_id / skill_name
    source_count = 0

    try:
        # 清理并准备工作目录
        if work_root.exists():
            await asyncio.to_thread(shutil.rmtree, str(work_root))
        await asyncio.to_thread(work_root.mkdir, parents=True, exist_ok=True)

        # 复制 skill 源到工作目录，保证每个生成任务隔离
        nuwa_work = work_root / "nuwa-agent-skill"
        await _copytree_async(NUWA_SOURCE, nuwa_work)
        _publish(skill_id, "main", "阶段 0/5：准备 Deep Agent 实例…")

        agent = create_nvwa_agent(root_dir=work_root)

        prompt = f"蒸馏 {display_name}"
        if description:
            prompt += f"\n补充说明：{description}"
        _publish(skill_id, "main", f"阶段 1/5：开始联网调研 {display_name}…")

        # 真流式迭代：每完成一个图节点就收到事件
        async for event in agent.astream({"messages": [{"role": "user", "content": prompt}]}):
            await _handle_event(skill_id, event)

        # 查找产物目录：agent 写入 skill-distill/{skill_name}/ 或 skill-distill/{display_name}/
        work_distill = work_root / "skill-distill"
        produced = work_distill / skill_name
        if not produced.exists():
            produced = work_distill / display_name
        if not produced.exists():
            # 兜底：取 skill-distill 下唯一目录
            candidates = [p for p in work_distill.iterdir() if p.is_dir()]
            if candidates:
                produced = candidates[0]

        if not produced.exists():
            raise FileNotFoundError(f"Agent did not produce output in {work_distill}")

        # 复制产物到最终 skills 目录
        await _copytree_async(produced, final_dir)
        source_count = await _count_files(final_dir / "references")
        file_count = await _count_files(final_dir)
        quote = await _extract_quote(final_dir)

        _publish(
            skill_id,
            "done",
            f"生成完成，共 {file_count} 个文件（{source_count} 个来源）",
            {"file_count": file_count, "source_count": source_count},
        )

        # 更新数据库元数据
        async with async_session_factory() as session:
            repo = CharacterRepository(session)
            skill = await repo.find_by_id(skill_id)
            if skill:
                await repo.update(
                    skill,
                    status="ready",
                    description=quote or description or f"{display_name} 的角色技能",
                    source_count=source_count,
                )

    except Exception as exc:
        logger.exception("full skill generation failed: %s", skill_id)
        _publish(skill_id, "error", f"生成失败：{exc}")
        async with async_session_factory() as session:
            repo = CharacterRepository(session)
            skill = await repo.find_by_id(skill_id)
            if skill:
                await repo.update(skill, status="error")
