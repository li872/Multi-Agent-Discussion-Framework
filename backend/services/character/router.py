# HTTP 接口

import json
import time

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from backend.config import settings
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


@router.post("/{skill_id}/copy")
async def copy_character(
    skill_id: str,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    # 把公开画廊角色复制到当前用户（需登录）
    character = await svc.copy_character(skill_id, user_id)
    return Result.ok(character)


@router.post("/{skill_id}/generate")
async def generate_full_character(
    skill_id: str,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    # 完整 Nuwa 管线生成：对已有角色触发 deepagent + Tavily 多阶段生成
    character = await svc.generate_full_skill(user_id, skill_id)
    return Result.ok(character)


@router.get("/{skill_id}/generation-progress")
async def generation_progress(
    skill_id: str,
    request: Request,
):
    # SSE：订阅 Redis generation:{skill_id}:events 通道，推送进度事件
    async def event_generator():
        r = redis.from_url(settings.redis_url, decode_responses=True)
        channel = f"generation:{skill_id}:events"
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        last_heartbeat = time.monotonic()
        try:
            yield "event: heartbeat\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg and msg.get("type") == "message":
                    payload = json.loads(msg["data"])
                    event_type = payload.get("event", "generation_progress")
                    data = json.dumps(payload.get("data", {}), ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {data}\n\n"
                elif time.monotonic() - last_heartbeat >= 15:
                    yield "event: heartbeat\ndata: {}\n\n"
                    last_heartbeat = time.monotonic()
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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