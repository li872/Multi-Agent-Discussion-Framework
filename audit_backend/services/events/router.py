# 审计事件：不直连业务表，转发到主后端 /api/v1/admin/audit/events
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from audit_backend.config import settings
from audit_backend.core.responses import Result
from audit_backend.deps import require_audit_admin
from backend.middleware.admin_auth import issue_admin_jwt

router = APIRouter(prefix="/api/v1/audit", tags=["audit-events"])


@router.get("/events")
async def list_events(
    user_id: str | None = Query(default=None),
    discussion_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    level: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_audit_admin),
) -> Result:
    if not (settings.admin_jwt_secret or settings.admin_token):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_JWT_SECRET 未配置，无法读取主系统审计事件",
        )
    params: dict = {"limit": limit, "offset": offset}
    if user_id:
        params["user_id"] = user_id
    if discussion_id:
        params["discussion_id"] = discussion_id
    if event_type:
        params["event_type"] = event_type
    if level:
        params["level"] = level
    url = f"{settings.main_api_base.rstrip('/')}/api/v1/admin/audit/events"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {issue_admin_jwt()}"},
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"主系统不可达: {e}",
        ) from e
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    body = resp.json()
    return Result.ok(body.get("data"))
