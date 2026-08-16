# 管理后台接口：主后端侧，供审计后台代理调用。路径 /api/v1/admin/*
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.core.health import probe_components
from backend.core.responses import Result
from backend.middleware.admin_auth import require_admin_jwt
from backend.services.admin.service import AdminService, get_admin_service

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_jwt)],
)


class StatusBody(BaseModel):
    enabled: bool


class PasswordBody(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class VisibilityBody(BaseModel):
    is_public: bool


class UsernameBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)


class PhoneBody(BaseModel):
    phone: str | None = Field(default=None, min_length=11, max_length=20)


class UserCreateBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    phone: str | None = Field(default=None, min_length=11, max_length=20)


@router.get("/audit/events")
async def list_audit_events(
    user_id: str | None = Query(default=None),
    discussion_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    level: str | None = Query(default=None, pattern="^(P0|P1|P2)$"),
    after_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    items, total = await svc.list_audit_events(
        user_id=user_id,
        discussion_id=discussion_id,
        event_type=event_type,
        level=level,
        after_id=after_id,
        limit=limit,
        offset=offset,
    )
    return Result.ok(
        {
            "items": [svc._event_dict(e) for e in items],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/audit/events/{event_id}")
async def get_audit_event(
    event_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.get_audit_event(event_id))


@router.get("/audit/operations")
async def list_operations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.list_operations(page, page_size))


@router.get("/audit/operations/{event_id}")
async def get_operation(
    event_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.get_audit_event(event_id))


@router.get("/health")
async def admin_health() -> Result:
    return Result.ok(await probe_components())


@router.get("/health/errors")
async def health_errors(svc: AdminService = Depends(get_admin_service)) -> Result:
    return Result.ok(await svc.list_health_errors())


@router.get("/health/errors/{event_id}")
async def health_error_detail(
    event_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.get_audit_event(event_id))


@router.get("/health/load")
async def health_load(svc: AdminService = Depends(get_admin_service)) -> Result:
    return Result.ok(await svc.system_load())


@router.get("/health/orphans")
async def health_orphans(svc: AdminService = Depends(get_admin_service)) -> Result:
    return Result.ok(await svc.list_orphans())


@router.get("/stats/overview")
async def stats_overview(svc: AdminService = Depends(get_admin_service)) -> Result:
    return Result.ok(await svc.stats_overview())


@router.get("/stats/tokens")
async def stats_tokens(svc: AdminService = Depends(get_admin_service)) -> Result:
    return Result.ok(await svc.token_stats())


@router.get("/stats/token-trend")
async def stats_token_trend(svc: AdminService = Depends(get_admin_service)) -> Result:
    return Result.ok(await svc.token_trend())


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.list_users(page, page_size, search))


@router.post("/users")
async def create_user(
    body: UserCreateBody, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.create_user(body.username, body.password, body.phone))


@router.get("/users/{user_id}")
async def get_user(
    user_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.get_user(user_id))


@router.put("/users/{user_id}/status")
async def set_user_status(
    user_id: str, body: StatusBody, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.set_user_status(user_id, body.enabled))


@router.put("/users/{user_id}/password")
async def reset_password(
    user_id: str, body: PasswordBody, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.reset_password(user_id, body.password))


@router.put("/users/{user_id}/username")
async def set_username(
    user_id: str, body: UsernameBody, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.set_username(user_id, body.username))


@router.put("/users/{user_id}/phone")
async def set_phone(
    user_id: str, body: PhoneBody, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.set_phone(user_id, body.phone))


@router.get("/users/{user_id}/tokens")
async def user_tokens(
    user_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.user_tokens(user_id))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.delete_user(user_id))


@router.get("/characters")
async def list_characters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.list_characters(page, page_size, search))


@router.get("/characters/{skill_id}")
async def get_character(
    skill_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.get_character(skill_id))


@router.put("/characters/{skill_id}/visibility")
async def set_character_visibility(
    skill_id: str, body: VisibilityBody, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.set_character_visibility(skill_id, body.is_public))


@router.delete("/characters/{skill_id}")
async def delete_character(
    skill_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.delete_character(skill_id))


@router.get("/gallery")
async def list_gallery(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.list_gallery(page, page_size, search))


@router.post("/gallery/{skill_id}/unlist")
async def unlist_gallery(
    skill_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.unlist_gallery(skill_id))


@router.get("/discussions")
async def list_discussions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.list_discussions(page, page_size, search))


@router.get("/discussions/{discussion_id}")
async def get_discussion(
    discussion_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.get_discussion(discussion_id))


@router.get("/discussions/{discussion_id}/messages")
async def discussion_messages(
    discussion_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    data = await svc.get_discussion(discussion_id)
    return Result.ok({"items": data["messages"]})


@router.get("/discussions/{discussion_id}/stream")
async def discussion_admin_stream(
    discussion_id: str,
    request: Request,
    after: str | None = Query(default=None),
):
    import json
    import time

    import redis.asyncio as redis

    from backend.config import settings as app_settings
    from backend.services.realtime.router import HEARTBEAT_SEC, _sse
    from backend.services.realtime.sse_manager import claim_stream, release_stream

    async def event_generator():
        stop = await claim_stream(discussion_id, "audit-listen")
        r = redis.from_url(app_settings.redis_url, decode_responses=True)
        channel = f"discussion:{discussion_id}:events"
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        last_heartbeat = time.monotonic()
        try:
            yield _sse("heartbeat", {"watch": True})
            while True:
                if stop.is_set() or await request.is_disconnected():
                    break
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg and msg.get("type") == "message":
                    payload = json.loads(msg["data"])
                    yield _sse(payload.get("event", "message"), payload.get("data", {}))
                elif time.monotonic() - last_heartbeat >= HEARTBEAT_SEC:
                    yield _sse("heartbeat", {"watch": True})
                    last_heartbeat = time.monotonic()
        finally:
            await release_stream(discussion_id, "audit-listen", stop)
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await r.aclose()

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/discussions/{discussion_id}/tokens")
async def discussion_tokens(
    discussion_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.discussion_tokens(discussion_id))


@router.delete("/discussions/{discussion_id}")
async def delete_discussion(
    discussion_id: str, svc: AdminService = Depends(get_admin_service)
) -> Result:
    return Result.ok(await svc.delete_discussion(discussion_id))
