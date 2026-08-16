# GET /api/v1/discussions/{id}/stream —— 浏览器用 EventSource 收实时事件
import json
import time

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.deps import decode_user_id
from backend.services.discussion.service import DiscussionService, get_discussion_service
from backend.services.realtime.catchup import (
    CATCHUP_BATCH_SIZE,
    CATCHUP_TAIL,
    catchup_mode,
    chunk_items,
)
from backend.services.realtime.sse_manager import claim_stream, release_stream

router = APIRouter(prefix="/api/v1/discussions", tags=["realtime"])
HEARTBEAT_SEC = 30


def _sse(event: str, data: dict | list) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/{discussion_id}/stream")
async def discussion_stream(
    discussion_id: str,
    request: Request,
    after: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    access_token: str | None = Query(default=None),
    svc: DiscussionService = Depends(get_discussion_service),
):
    user_id = decode_user_id(access_token)

    async def event_generator():
        stop = await claim_stream(discussion_id, user_id)
        r = redis.from_url(settings.redis_url, decode_responses=True)
        channel = f"discussion:{discussion_id}:events"
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        last_heartbeat = time.monotonic()
        try:
            if after:
                count = await svc.count_messages_after(discussion_id, after)
                mode = catchup_mode(count)
                if mode == "each":
                    backlog = await svc.list_messages_after(discussion_id, after)
                    for msg in backlog:
                        yield _sse("message", msg.model_dump())
                elif mode == "batch":
                    backlog = await svc.list_messages_after(discussion_id, after)
                    for batch in chunk_items(
                        [m.model_dump() for m in backlog], CATCHUP_BATCH_SIZE
                    ):
                        yield _sse("catchup_batch", {"items": batch})
                else:
                    summary = {
                        "total": count,
                        "skipped": count - CATCHUP_TAIL,
                        "message": "消息过多，仅显示最近 20 条，完整记录请查看回放",
                    }
                    yield _sse("catchup_summary", summary)
                    tail = await svc.list_messages_after(
                        discussion_id, after, limit=CATCHUP_TAIL, newest_first=True
                    )
                    for msg in tail:
                        yield _sse("message", msg.model_dump())

            yield _sse("heartbeat", {})
            while True:
                if stop.is_set() or await request.is_disconnected():
                    break
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg and msg.get("type") == "message":
                    payload = json.loads(msg["data"])
                    event_type = payload.get("event", "message")
                    yield _sse(event_type, payload.get("data", {}))
                elif time.monotonic() - last_heartbeat >= HEARTBEAT_SEC:
                    yield _sse("heartbeat", {})
                    last_heartbeat = time.monotonic()
        finally:
            await release_stream(discussion_id, user_id, stop)
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
