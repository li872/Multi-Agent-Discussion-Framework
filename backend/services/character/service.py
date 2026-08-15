#  业务：建目录 + 写库
# 核心流程（创建角色）：
# 1. 拼 skill 目录名（名字-perspective）
# 2. 磁盘创建文件夹 + 写初始 SKILL.md
# 3. PG 插入 skills 行（file_path 指向目录）
import asyncio
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_engine.skill_gen.mini_generate import run_mini_skill_generation
from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
from backend.services.character.file_manager import SkillFileManager
from backend.services.character.repository import CharacterRepository
from backend.services.character.schemas import CharacterListResponse, CharacterResponse


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