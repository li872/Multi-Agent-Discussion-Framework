#  业务：建目录 + 写库
# 核心流程（创建角色）：
# 1. 拼 skill 目录名（名字-perspective）
# 2. 磁盘创建文件夹 + 写初始 SKILL.md
# 3. PG 插入 skills 行（file_path 指向目录）
# 同时把 skill.create / skill.generate / skill.copy / skill.update / skill.delete 等事件写入 audit_events。
import asyncio
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_engine.llm import get_chat_llm
from agent_engine.skill_gen.generation_service import run_full_skill_generation
from agent_engine.skill_gen.mini_generate import run_mini_skill_generation
from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
from backend.services.audit import AuditRepository
from backend.services.character.file_manager import SkillFileManager
from backend.services.character.repository import CharacterRepository
from backend.services.character.schemas import (
    CharacterListResponse,
    CharacterResponse,
    RecommendationsResponse,
)

# 人物推荐兜底池：覆盖科技、商业、哲学、科学等领域
DEFAULT_RECOMMENDATIONS = [
    "Steve Jobs",
    "Elon Musk",
    "Warren Buffett",
    "Charlie Munger",
    "Naval Ravikant",
    "Paul Graham",
    "Richard Feynman",
    "Nassim Taleb",
    "Yuval Noah Harari",
    "Daniel Kahneman",
    "Jeff Bezos",
    "Bill Gates",
    "Albert Einstein",
    "Marie Curie",
    "Leonardo da Vinci",
    "Confucius",
    "Laozi",
    "Sun Tzu",
    "Socrates",
    "Plato",
    "Aristotle",
    "Marcus Aurelius",
    "Seneca",
    "Montaigne",
    "Shakespeare",
    "Goethe",
    "Tolstoy",
    "Kafka",
    "Mark Twain",
    "Benjamin Franklin",
    "Nikola Tesla",
    "Alan Turing",
    "Ada Lovelace",
    "Linus Torvalds",
    "Andrej Karpathy",
    "Ilya Sutskever",
]


class CharacterService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CharacterRepository(session)
        self.audit = AuditRepository(session)
        self.fm = SkillFileManager()

    async def create_character(
        self, owner_id: str, name: str, description: str, tags: list[str], is_public: bool
    ) -> CharacterResponse:
        uid = uuid.UUID(owner_id)
        skill_name = f"{name}-perspective" if not name.endswith("-perspective") else name
        existing = await self.repo.find_by_owner_and_name(uid, skill_name)
        if existing:
            raise BusinessException(ErrorCode.SKILL_NAME_EXISTS)

        await self.fm.create_skill_dir(owner_id, skill_name)
        await self.fm.write_file(
            owner_id, skill_name, "SKILL.md", f"# {name}\n\n> {description}\n"
        )
        skill = await self.repo.create(
            owner_id=uid,
            name=skill_name,
            description=description,
            file_path=f"{owner_id}/{skill_name}",
            tags=tags,
            is_public=is_public,
            status="ready",
        )
        # 角色创建是 P2 数据变更事件，记录元数据方便后台追溯
        await self.audit.record(
            event_type="skill.create",
            level="P2",
            user_id=uid,
            payload={
                "skill_id": str(skill.id),
                "skill_name": skill_name,
                "is_public": is_public,
            },
        )
        await self.session.commit()
        return await self._to_response(skill)

    async def generate_character(
        self, owner_id: str, name: str, description: str = ""
    ) -> CharacterResponse:
        """学习版 AI 生成：先落库 generating，再后台 LLM 写 SKILL.md。"""
        uid = uuid.UUID(owner_id)
        display_name = name.strip()
        skill_name = (
            f"{display_name}-perspective"
            if not display_name.endswith("-perspective")
            else display_name
        )
        existing = await self.repo.find_by_owner_and_name(uid, skill_name)
        if existing:
            raise BusinessException(ErrorCode.SKILL_NAME_EXISTS)

        await self.fm.create_skill_dir(owner_id, skill_name)
        await self.fm.write_file(
            owner_id,
            skill_name,
            "SKILL.md",
            f"# {display_name}\n\n> 生成中…\n",
        )
        # status=generating：列表可立刻看到「生成中」；真正内容由后台任务覆盖
        skill = await self.repo.create(
            owner_id=uid,
            name=skill_name,
            description=description or f"正在生成 {display_name}",
            file_path=f"{owner_id}/{skill_name}",
            tags=[],
            is_public=False,
            status="generating",
        )

        # 触发 AI 生成即记录 P0 资源消耗事件（LLM/Tavily 调用），后台任务完成后再补一条 complete/error
        await self.audit.record(
            event_type="skill.generate",
            level="P0",
            user_id=uid,
            payload={
                "skill_id": str(skill.id),
                "skill_name": skill_name,
                "query": display_name,
            },
        )
        await self.session.commit()

        # 与「开始讨论」相同：HTTP 先返回，LLM 不阻塞接口
        asyncio.create_task(
            run_mini_skill_generation(
                skill_id=skill.id,
                owner_id=owner_id,
                skill_name=skill_name,
                display_name=display_name.replace("-perspective", ""),
                description=description,
            )
        )
        return await self._to_response(skill)

    async def generate_full_skill(self, user_id: str, skill_id: str) -> CharacterResponse:
        """完整 Nuwa 管线生成：对已有角色触发 deepagent + Tavily 多阶段生成。"""
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        if str(skill.owner_id) != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN, "Not your character")
        if skill.status == "generating":
            raise BusinessException(
                ErrorCode.DISCUSSION_INVALID_STATUS,
                "Character is already generating",
            )

        display_name = skill.name.replace("-perspective", "")
        await self.repo.update(skill, status="generating")

        # 完整 Nuwa 管线涉及 Tavily 搜索 + 多 Agent 并行，属于 P0 资源消耗审计
        await self.audit.record(
            event_type="skill.generate",
            level="P0",
            user_id=user_id,
            payload={
                "skill_id": str(skill.id),
                "skill_name": skill.name,
                "query": display_name,
            },
        )
        await self.session.commit()

        # 后台运行完整 Nuwa 管线；HTTP 立即返回，前端通过 SSE 看进度
        asyncio.create_task(
            run_full_skill_generation(
                skill_id=skill.id,
                owner_id=user_id,
                skill_name=skill.name,
                display_name=display_name,
                description=skill.description or "",
            )
        )
        return await self._to_response(skill)

    async def get_recommendations(self, owner_id: str) -> RecommendationsResponse:
        """人物推荐：优先用 LLM 生成 6 个人名，失败或不足时用兜底池补齐。"""
        uid = uuid.UUID(owner_id)
        skills, _ = await self.repo.list_by_owner(uid, page=1, page_size=1000)
        existing = {
            s.name.replace("-perspective", "").lower()
            for s in skills
            if s.name
        }

        llm_names: list[str] = []
        try:
            llm = get_chat_llm(temperature=0.9, timeout=8)
            prompt = (
                "请推荐 6 位适合作为 AI 圆桌讨论角色的历史/公众人物，"
                "涵盖科技、商业、哲学、科学等领域。只返回 6 个人名，每行一个，不要解释。"
            )
            raw = (await llm.ainvoke(prompt)).content
            if isinstance(raw, str):
                for line in raw.splitlines():
                    name = line.strip().strip("-*1234567890. ").strip()
                    if name and len(name) <= 64 and name.lower() not in existing:
                        llm_names.append(name)
        except Exception:
            # LLM 失败或 key 未配置：静默回退到兜底池
            pass

        candidates = list(llm_names)
        for name in DEFAULT_RECOMMENDATIONS:
            if name.lower() not in existing and name not in candidates:
                candidates.append(name)
            if len(candidates) >= 6:
                break

        source = "llm" if len(llm_names) >= 6 else "fallback"
        return RecommendationsResponse(items=candidates[:6], source=source)

    async def list_my_characters(
        self, owner_id: str, page: int, page_size: int, search: str | None
    ) -> CharacterListResponse:
        skills, total = await self.repo.list_by_owner(
            uuid.UUID(owner_id), page, page_size, search
        )
        items = await asyncio.gather(*[self._to_response(s) for s in skills])
        return CharacterListResponse(
            items=list(items),
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    async def list_gallery(
        self, page: int, page_size: int, search: str | None
    ) -> CharacterListResponse:
        skills, total = await self.repo.list_public(page, page_size, search)
        items = await asyncio.gather(*[self._to_response(s) for s in skills])
        return CharacterListResponse(
            items=list(items),
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    async def copy_character(self, skill_id: str, user_id: str) -> CharacterResponse:
        """把公开画廊角色复制到当前用户（文件 + PG 元数据）。"""
        src = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not src or not src.is_public or src.status != "ready":
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND, "Public skill not found")

        uid = uuid.UUID(user_id)
        base_name = src.name
        dst_name = base_name
        # 重名则加后缀，避免唯一约束冲突
        for i in range(0, 20):
            candidate = base_name if i == 0 else f"{base_name.rstrip('-perspective')}-copy{i}-perspective"
            if not candidate.endswith("-perspective"):
                candidate = f"{candidate}-perspective"
            exists = await self.repo.find_by_owner_and_name(uid, candidate)
            if not exists:
                dst_name = candidate
                break
        else:
            raise BusinessException(ErrorCode.SKILL_NAME_EXISTS, "Too many copies")

        try:
            await self.fm.copy_skill_dir(
                str(src.owner_id), src.name, user_id, dst_name
            )
        except FileNotFoundError:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND, "Skill files missing")

        skill = await self.repo.create(
            owner_id=uid,
            name=dst_name,
            description=src.description,
            file_path=f"{user_id}/{dst_name}",
            tags=list(src.tags or []),
            is_public=False,
            status="ready",
        )
        # 跨用户复制属于 P1 跨用户操作，必须记录源和目标的归属
        await self.audit.record(
            event_type="skill.copy",
            level="P1",
            user_id=uid,
            payload={
                "src_skill_id": str(src.id),
                "src_owner_id": str(src.owner_id),
                "dst_skill_id": str(skill.id),
                "dst_skill_name": dst_name,
            },
        )
        await self.session.commit()
        return await self._to_response(skill)

    async def get_character(self, skill_id: str, user_id: str = "") -> CharacterResponse:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        self._ensure_can_read(skill, user_id)
        return await self._to_response(skill)

    async def update_character(self, skill_id: str, user_id: str, **kwargs) -> CharacterResponse:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        self._ensure_can_write(skill, user_id)
        changed_fields = {k: v for k, v in kwargs.items() if getattr(skill, k) != v}
        skill = await self.repo.update(skill, **kwargs)
        if changed_fields:
            # 角色元数据变更属于 P2 数据修改事件；公开/可见性切换单独按 skill.visibility_changed 处理
            event_type = "skill.visibility_changed" if "is_public" in changed_fields else "skill.update"
            await self.audit.record(
                event_type=event_type,
                level="P1" if event_type == "skill.visibility_changed" else "P2",
                user_id=uuid.UUID(user_id),
                payload={
                    "skill_id": skill_id,
                    "skill_name": skill.name,
                    "changed_fields": list(changed_fields.keys()),
                },
            )
            await self.session.commit()
        return await self._to_response(skill)

    async def delete_character(self, skill_id: str, owner_id: str) -> None:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        if str(skill.owner_id) != owner_id:
            raise BusinessException(ErrorCode.FORBIDDEN)
        await self.fm.delete_skill_dir(str(skill.owner_id), skill.name)
        await self.repo.soft_delete(skill)
        # 删除是 P1 生命周期事件，保留被删角色名和 owner，便于追溯
        await self.audit.record(
            event_type="skill.delete",
            level="P1",
            user_id=uuid.UUID(owner_id),
            payload={
                "skill_id": skill_id,
                "skill_name": skill.name,
            },
        )
        await self.session.commit()

    async def list_files(self, skill_id: str, user_id: str) -> list[str]:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        self._ensure_can_read(skill, user_id)
        return await self.fm.list_files(str(skill.owner_id), skill.name)

    async def read_file(self, skill_id: str, path: str, user_id: str) -> str:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        self._ensure_can_read(skill, user_id)
        try:
            return await self.fm.read_file(str(skill.owner_id), skill.name, path)
        except FileNotFoundError:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND, f"File not found: {path}")

    async def write_file(self, skill_id: str, path: str, content: str, user_id: str) -> None:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        self._ensure_can_write(skill, user_id)
        await self.fm.write_file(str(skill.owner_id), skill.name, path, content)
        # 文件写入是 P2 数据修改事件，记录被修改 skill 和文件路径，便于内容变更追溯
        await self.audit.record(
            event_type="skill.file_write",
            level="P2",
            user_id=uuid.UUID(user_id),
            payload={
                "skill_id": skill_id,
                "skill_name": skill.name,
                "file_path": path,
            },
        )
        await self.session.commit()

    def _ensure_can_read(self, skill, user_id: str) -> None:
        if skill.is_public:
            return
        if not user_id or str(skill.owner_id) != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN)

    def _ensure_can_write(self, skill, user_id: str) -> None:
        if str(skill.owner_id) != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN)

    @staticmethod
    def _extract_quotes(content: str, limit: int = 5) -> list[str]:
        """从 SKILL.md 提取以 > 开头的引用语，最多 limit 条。"""
        quotes: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith(">"):
                continue
            quote = stripped.lstrip(">").strip()
            if quote:
                quotes.append(quote)
            if len(quotes) >= limit:
                break
        return quotes

    async def _to_response(self, skill) -> CharacterResponse:
        # 读磁盘 SKILL.md 提取引用语；文件缺失时退回数据库 description
        quotes: list[str] = []
        try:
            content = await self.fm.read_file(
                str(skill.owner_id), skill.name, "SKILL.md"
            )
            quotes = self._extract_quotes(content)
        except Exception:
            quotes = []

        description = quotes[0] if quotes else (skill.description or "")
        return CharacterResponse(
            id=str(skill.id),
            owner_id=str(skill.owner_id),
            name=skill.name.replace("-perspective", ""),
            description=description,
            tags=skill.tags or [],
            is_public=skill.is_public,
            status=skill.status,
            created_at=skill.created_at.isoformat(),
            updated_at=skill.updated_at.isoformat(),
            quotes=quotes,
        )


async def get_character_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(db)