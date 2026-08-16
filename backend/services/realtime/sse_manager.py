# 同一 user + discussion：新 SSE 连接取消旧 Task
from __future__ import annotations

import asyncio

_lock = asyncio.Lock()
_active: dict[tuple[str, str], asyncio.Event] = {}


async def claim_stream(discussion_id: str, user_id: str) -> asyncio.Event:
    key = (discussion_id, user_id or "anon")
    stop = asyncio.Event()
    async with _lock:
        prev = _active.get(key)
        if prev is not None:
            prev.set()
        _active[key] = stop
    return stop


async def release_stream(discussion_id: str, user_id: str, stop: asyncio.Event) -> None:
    key = (discussion_id, user_id or "anon")
    async with _lock:
        if _active.get(key) is stop:
            del _active[key]
