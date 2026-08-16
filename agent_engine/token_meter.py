# 从 LangChain 响应 / 流式 chunk 提取 token，并写入 token_usages。

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


def extract_token_count(message) -> int:
    """从 AIMessage / ChatGeneration chunk 读取用量；没有则返回 0。"""
    if message is None:
        return 0
    usage = getattr(message, "usage_metadata", None) or {}
    if isinstance(usage, dict):
        total = usage.get("total_tokens")
        if total is not None:
            return max(0, int(total))
        inp = int(usage.get("input_tokens") or 0)
        out = int(usage.get("output_tokens") or 0)
        if inp or out:
            return inp + out
    meta = getattr(message, "response_metadata", None) or {}
    if isinstance(meta, dict):
        tu = meta.get("token_usage") or meta.get("usage") or {}
        if isinstance(tu, dict):
            total = tu.get("total_tokens") or tu.get("totalTokens")
            if total is not None:
                return max(0, int(total))
            inp = int(tu.get("prompt_tokens") or tu.get("input_tokens") or 0)
            out = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)
            if inp or out:
                return inp + out
    return 0


def estimate_tokens_from_text(*parts: str) -> int:
    text = "".join(p for p in parts if p)
    if not text:
        return 0
    return max(1, len(text) // 4)


async def record_token_usage(
    *,
    tokens: int,
    user_id: uuid.UUID | str | None = None,
    discussion_id: uuid.UUID | str | None = None,
    kind: str = "llm",
) -> None:
    """独立 session 写入，失败只打日志，不打断主流程。"""
    if tokens <= 0:
        return
    try:
        from backend.deps import async_session_factory
        from backend.services.admin.token_repository import TokenUsageRepository

        async with async_session_factory() as session:
            repo = TokenUsageRepository(session)
            await repo.record(
                tokens=tokens,
                user_id=user_id,
                discussion_id=discussion_id,
                kind=kind,
            )
            await session.commit()
    except Exception:
        logger.exception(
            "record_token_usage failed tokens=%s discussion=%s",
            tokens,
            discussion_id,
        )
