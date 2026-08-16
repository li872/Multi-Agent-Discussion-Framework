# 审计员旁听讨论：query 里带 audit_token（EventSource 不能自定义 Header）
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt

from audit_backend.config import settings
from backend.middleware.admin_auth import issue_admin_jwt

router = APIRouter(prefix="/api/v1/audit/discussions", tags=["audit-listen"])


def _audit_user(access_token: str | None) -> str:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(
            access_token,
            settings.audit_jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="audit",
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    username = payload.get("sub") or ""
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username


@router.get("/{discussion_id}/stream")
async def listen_discussion(
    discussion_id: str,
    request: Request,
    access_token: str | None = Query(default=None),
    after: str | None = Query(default=None),
):
    _audit_user(access_token)
    if not (settings.admin_jwt_secret or settings.admin_token):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_JWT_SECRET 未配置",
        )
    params: dict = {"client_id": f"audit-{id(request)}"}
    if after:
        params["after"] = after
    url = f"{settings.main_api_base.rstrip('/')}/api/v1/admin/discussions/{discussion_id}/stream"

    async def gen():
        headers = {"Authorization": f"Bearer {issue_admin_jwt()}"}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url, params=params, headers=headers) as resp:
                    if resp.status_code >= 400:
                        yield f"event: error\ndata: {{\"status\":{resp.status_code}}}\n\n"
                        return
                    async for chunk in resp.aiter_bytes():
                        if await request.is_disconnected():
                            break
                        yield chunk
        except httpx.HTTPError as e:
            yield f"event: error\ndata: {{\"message\":\"{str(e)[:120]}\"}}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
