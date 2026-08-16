# 圆桌角色工厂：每个参与者一个 deepagent，SKILL.md 预加载进系统提示
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from agent_engine.llm import get_chat_llm

DISCUSSION_SYSTEM_PROMPT = """你就是 {skill_name} 本人。下面是你的完整记忆和思维框架。读完之后，你就是那个人——不是在扮演。

三条铁律：切题；不重复已经说过的经历；让观众带走新东西。

思考（决定要不要说话）时只输出 JSON：
{{"decision":"speak"|"wait", "confidence":0.76, "reasoning":"内心念头"}}
confidence 必须两位小数，禁止 0.50/0.70/0.80 这类整齐数字。

发言时纯文本，不要 JSON，不要说自己是 AI。数字必须来自技能文件，没有出处就不要编。
"""


def _load_skill_text(skill_dir: Path, max_chars: int = 40_000) -> str:
    # 先 SKILL.md，再 references，总长度封顶避免撑爆上下文
    parts: list[str] = []
    used = 0
    skill_md = skill_dir / "SKILL.md"
    ordered = [skill_md] if skill_md.exists() else []
    ordered.extend(
        p for p in sorted(skill_dir.rglob("*.md")) if p.resolve() != skill_md.resolve()
    )
    for md in ordered:
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        header = f"### {md.relative_to(skill_dir)}\n\n"
        chunk = header + text
        if used + len(chunk) > max_chars:
            remain = max_chars - used
            if remain > len(header) + 50:
                parts.append(header + text[: remain - len(header)] + "\n\n[截断]")
            break
        parts.append(chunk)
        used += len(chunk)
    return "\n\n---\n\n".join(parts)


def create_roundtable_agent(skill_path: str):
    """加载角色目录，返回 (deepagent 图, 展示名)。"""
    skill_dir = Path(skill_path).resolve()
    if not (skill_dir / "SKILL.md").exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_path}")

    skill_name = skill_dir.name.replace("-perspective", "")
    skill_content = _load_skill_text(skill_dir)
    prompt = DISCUSSION_SYSTEM_PROMPT.replace("{skill_name}", skill_name)
    prompt += f"\n\n## 你的技能文件\n\n{skill_content}"

    backend = FilesystemBackend(root_dir="/", virtual_mode=True)
    agent = create_deep_agent(
        model=get_chat_llm(temperature=0.7, timeout=30),
        system_prompt=prompt,
        skills=[str(skill_dir)],
        backend=backend,
    )
    return agent, skill_name
