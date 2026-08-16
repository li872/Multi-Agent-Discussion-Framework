# 审计员登录后，把 /api/v1/admin/* 原样转到主后端，带上 X-Admin-Token
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from audit_backend.config import settings
from audit_backend.deps import require_audit_admin

router = APIRouter(prefix="/api/v1/admin", tags=["admin-proxy"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_admin(
    path: str,
    request: Request,
    _: str = Depends(require_audit_admin),
) -> Response:
    if not settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_TOKEN 未配置",
        )
    url = f"{settings.main_api_base.rstrip('/')}/api/v1/admin/{path}"
    body = await request.body()
    headers = {
        "X-Admin-Token": settings.admin_token,
        "Content-Type": request.headers.get("content-type", "application/json"),
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.request(
                request.method,
                url,
                params=dict(request.query_params),
                content=body or None,
                headers=headers,
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"主系统不可达: {e}",
        ) from e
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )
