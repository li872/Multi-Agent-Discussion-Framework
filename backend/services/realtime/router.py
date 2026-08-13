# GET /api/v1/discussions/{id}/stream —— 浏览器用 EventSource 收实时事件

import asyncio
import json

import redis.asyncio as redis
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.config import settings

router = APIRouter(prefix="/api/v1/discussions", tags=["realtime"])


@router.get("/{discussion_id}/stream")
async def discussion_stream(discussion_id: str, request: Request):
    async def event_generator():
        r = redis.from_url(settings.redis_url, decode_responses=True)
        channel = f"discussion:{discussion_id}:events"
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
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
                    event_type = payload.get("event", "message")
                    data = json.dumps(payload.get("data", {}), ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {data}\n\n"
                else:
                    # 定期心跳，避免代理断开空闲连接
                    yield "event: heartbeat\ndata: {}\n\n"
                    await asyncio.sleep(15)
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