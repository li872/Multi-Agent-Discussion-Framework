# 作用： 编排写完消息后，往 Redis 推一条

# 把讨论事件 publish 到 Redis，供 SSE 订阅端推给前端

import json

import redis.asyncio as redis

from backend.config import settings

_redis: redis.Redis | None = None


async def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish_discussion_event(
    discussion_id: str,
    event: str,
    data: dict,
) -> None:
    r = await _get_redis()
    channel = f"discussion:{discussion_id}:events"
    payload = json.dumps({"event": event, "data": data}, ensure_ascii=False)
    await r.publish(channel, payload)


async def publish_generation_event(
    skill_id: str,
    data: dict,
) -> None:
    # Skill 生成进度事件：与 discussion 事件使用不同 channel，避免串流
    r = await _get_redis()
    channel = f"generation:{skill_id}:events"
    payload = json.dumps({"event": "generation_progress", "data": data}, ensure_ascii=False)
    await r.publish(channel, payload)

