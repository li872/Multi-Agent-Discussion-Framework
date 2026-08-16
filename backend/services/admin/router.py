# 管理后台接口：主后端侧，供审计后台代理调用。
#
# 路径约定：/api/v1/admin/*
# 权限：当前用 X-Admin-Token 请求头做简单校验，后续升级为审计后端签发的服务 JWT。
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from backend.config import settings
from backend.core.responses import Result
from backend.services.admin.service import AdminService, get_admin_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """简单 admin token 校验；未配置或 token 不符则拒绝。"""
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin token",
        )


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
    """查询审计事件。

    这是审计后台追溯功能的数据源，支持按 user_id / discussion_id /
    event_type / level 筛选，以及 after_id 游标分页。
    """
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
