# HTTP 接口

from fastapi import APIRouter, Depends, Query

from backend.core.responses import Result
from backend.deps import get_current_user, require_user
from backend.services.character.schemas import (
    CharacterCreateRequest,
    CharacterGenerateRequest,
    CharacterResponse,
    CharacterUpdateRequest,
    FileContentRequest,
)
from backend.services.character.service import CharacterService, get_character_service

router = APIRouter(prefix="/api/v1/characters", tags=["character"])


@router.post("")
async def create_character(
    req: CharacterCreateRequest,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    character = await svc.create_character(
        user_id, req.name, req.description, req.tags, req.is_public
    )
    return Result.ok(character)


# /generate 必须在 /{skill_id} 之前注册，否则 "generate" 会被当成 id
@router.post("/generate")
async def generate_character(
    req: CharacterGenerateRequest,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    character = await svc.generate_character(user_id, req.name, req.description)
    return Result.ok(character)


@router.get("")
async def list_my_characters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result:
    result = await svc.list_my_characters(user_id, page, page_size, search)
    return Result.ok(result)


# /gallery 必须在 /{skill_id} 之前注册，否则 "gallery" 会被当成 id
@router.get("/gallery")
async def list_public_characters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    svc: CharacterService = Depends(get_character_service),
) -> Result:
    # 学习版画廊：无需登录即可浏览公开角色
    result = await svc.list_gallery(page, page_size, search)
    return Result.ok(result)


@router.get("/{skill_id}")
async def get_character(
    skill_id: str,
    user_id: str = Depends(get_current_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    character = await svc.get_character(skill_id, user_id)
    return Result.ok(character)


@router.put("/{skill_id}")
async def update_character(
    skill_id: str,
    req: CharacterUpdateRequest,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    character = await svc.update_character(skill_id, user_id, **updates)
    return Result.ok(character)


@router.delete("/{skill_id}")
async def delete_character(
    skill_id: str,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[None]:
    await svc.delete_character(skill_id, user_id)
    return Result.ok(None)


@router.get("/{skill_id}/files")
async def list_or_read_files(
    skill_id: str,
    path: str | None = Query(default=None),
    user_id: str = Depends(get_current_user),
    svc: CharacterService = Depends(get_character_service),
):
    if path:
        content = await svc.read_file(skill_id, path, user_id)
        return Result.ok(content)
    files = await svc.list_files(skill_id, user_id)
    return Result.ok(files)


@router.put("/{skill_id}/files")
async def write_file(
    skill_id: str,
    req: FileContentRequest,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[None]:
    await svc.write_file(skill_id, req.path, req.content or "", user_id)
    return Result.ok(None)