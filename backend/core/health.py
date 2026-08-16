# 深度探活：给 Docker / 审计后台看组件是否活着
from __future__ import annotations

import asyncio
import time

import httpx
from sqlalchemy import text

from backend.config import settings
from backend.deps import async_session_factory


async def probe_components() -> dict:
    result: dict = {"app": settings.app_name, "components": {}}

    t0 = time.monotonic()
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        result["components"]["database"] = {
            "status": "healthy",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception as e:
        result["components"]["database"] = {"status": "unhealthy", "error": str(e)[:200]}

    t0 = time.monotonic()
    try:
        import redis.asyncio as aioredis

        r = aioredis.Redis(host=settings.redis_host, port=settings.redis_port)
        await asyncio.wait_for(r.ping(), timeout=3)
        await r.close()
        result["components"]["redis"] = {
            "status": "healthy",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception as e:
        result["components"]["redis"] = {"status": "unhealthy", "error": str(e)[:200]}

    t0 = time.monotonic()
    if not settings.llm_api_key:
        result["components"]["llm_api"] = {"status": "not_configured"}
    else:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{settings.llm_api_base.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                )
            result["components"]["llm_api"] = {
                "status": "healthy" if resp.status_code < 500 else "degraded",
                "latency_ms": round((time.monotonic() - t0) * 1000, 1),
                "http_status": resp.status_code,
            }
        except Exception as e:
            result["components"]["llm_api"] = {
                "status": "unhealthy",
                "error": str(e)[:200],
            }
    return result
