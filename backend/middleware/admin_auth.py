# 审计网关访问主后端 /api/v1/admin/*：短时 JWT + jti 一次性消费防重放
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from backend.config import settings

ADMIN_AUD = "admin"
_memory_jti: set[str] = set()


def _secret() -> str:
    return settings.admin_jwt_secret or settings.jwt_secret


def issue_admin_jwt(*, minutes: int = 5) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "audit-gateway",
        "aud": ADMIN_AUD,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def consume_jti_memory(jti: str) -> bool:
    if jti in _memory_jti:
        return False
    _memory_jti.add(jti)
    return True


async def consume_jti(jti: str) -> bool:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        ok = await asyncio.wait_for(
            r.set(f"madf:admin_jti:{jti}", "1", nx=True, ex=360),
            timeout=1.0,
        )
        await r.aclose()
        return bool(ok)
    except Exception:
        return consume_jti_memory(jti)


async def require_admin_jwt(
    authorization: str | None = Header(default=None),
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin JWT",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[settings.jwt_algorithm],
            audience=ADMIN_AUD,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin JWT",
        ) from exc
    jti = payload.get("jti") or ""
    if not jti or not await consume_jti(jti):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin JWT replayed or missing jti",
        )
    return payload.get("sub") or "audit-gateway"
