#  业务：建目录 + 写库
# 核心流程（创建角色）：
# 1. 拼 skill 目录名（名字-perspective）
# 2. 磁盘创建文件夹 + 写初始 SKILL.md
# 3. PG 插入 skills 行（file_path 指向目录）
import asyncio
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_engine.llm import get_chat_llm
from agent_engine.skill_gen.generation_service import run_full_skill_generation
from agent_engine.skill_gen.mini_generate import run_mini_skill_generation
from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
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
        self.repo = CharacterRepository(session)
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
        return self._to_response(skill)

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
        return self._to_response(skill)

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
        return self._to_response(skill)

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
        return CharacterListResponse(
            items=[self._to_response(s) for s in skills],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    async def list_gallery(
        self, page: int, page_size: int, search: str | None
    ) -> CharacterListResponse:
        skills, total = await self.repo.list_public(page, page_size, search)
        return CharacterListResponse(
            items=[self._to_response(s) for s in skills],
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
        return self._to_response(skill)

    async def get_character(self, skill_id: str, user_id: str = "") -> CharacterResponse:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        self._ensure_can_read(skill, user_id)
        return self._to_response(skill)

    async def update_character(self, skill_id: str, user_id: str, **kwargs) -> CharacterResponse:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        self._ensure_can_write(skill, user_id)
        skill = await self.repo.update(skill, **kwargs)
        return self._to_response(skill)

    async def delete_character(self, skill_id: str, owner_id: str) -> None:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        if str(skill.owner_id) != owner_id:
            raise BusinessException(ErrorCode.FORBIDDEN)
        await self.fm.delete_skill_dir(str(skill.owner_id), skill.name)
        await self.repo.soft_delete(skill)

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

    def _ensure_can_read(self, skill, user_id: str) -> None:
        if skill.is_public:
            return
        if not user_id or str(skill.owner_id) != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN)

    def _ensure_can_write(self, skill, user_id: str) -> None:
        if str(skill.owner_id) != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN)

    @staticmethod
    def _to_response(skill) -> CharacterResponse:
        return CharacterResponse(
            id=str(skill.id),
            owner_id=str(skill.owner_id),
            name=skill.name.replace("-perspective", ""),
            description=skill.description,
            tags=skill.tags or [],
            is_public=skill.is_public,
            status=skill.status,
            created_at=skill.created_at.isoformat(),
            updated_at=skill.updated_at.isoformat(),
        )


async def get_character_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(db)