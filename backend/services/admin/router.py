# 管理后台接口：主后端侧，供审计后台代理调用。路径 /api/v1/admin/*
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.config import settings
from backend.core.health import probe_components
from backend.core.responses import Result
from backend.services.admin.service import AdminService, get_admin_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin token",
        )


class StatusBody(BaseModel):
    enabled: bool


class PasswordBody(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class VisibilityBody(BaseModel):
    is_public: bool


@router.get("/audit/events")
async def list_audit_events(
    user_id: str | None = Query(default=None),
    discussion_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    level: str | None = Query(default=None, pattern="^(P0|P1|P2)$"),
    after_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_require_admin_token),
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
            "items": [
                {
                    "id": str(e.id),
                    "user_id": str(e.user_id) if e.user_id else None,
                    "discussion_id": str(e.discussion_id) if e.discussion_id else None,
                    "event_type": e.event_type,
                    "level": e.level,
                    "payload": e.payload,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in items
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/health")
async def admin_health(
    _: None = Depends(_require_admin_token),
) -> Result:
    return Result.ok(await probe_components())


@router.get("/stats/overview")
async def stats_overview(
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.stats_overview())


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.list_users(page, page_size, search))


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.get_user(user_id))


@router.put("/users/{user_id}/status")
async def set_user_status(
    user_id: str,
    body: StatusBody,
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.set_user_status(user_id, body.enabled))


@router.put("/users/{user_id}/password")
async def reset_password(
    user_id: str,
    body: PasswordBody,
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.reset_password(user_id, body.password))


@router.get("/characters")
async def list_characters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.list_characters(page, page_size, search))


@router.put("/characters/{skill_id}/visibility")
async def set_character_visibility(
    skill_id: str,
    body: VisibilityBody,
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.set_character_visibility(skill_id, body.is_public))


@router.delete("/characters/{skill_id}")
async def delete_character(
    skill_id: str,
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.delete_character(skill_id))


@router.get("/discussions")
async def list_discussions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.list_discussions(page, page_size, search))


@router.get("/discussions/{discussion_id}")
async def get_discussion(
    discussion_id: str,
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.get_discussion(discussion_id))


@router.delete("/discussions/{discussion_id}")
async def delete_discussion(
    discussion_id: str,
    _: None = Depends(_require_admin_token),
    svc: AdminService = Depends(get_admin_service),
) -> Result:
    return Result.ok(await svc.delete_discussion(discussion_id))
