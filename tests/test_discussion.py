from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.core.exceptions import BusinessException, ErrorCode
from backend.services.discussion.schemas import DiscussionCreateRequest, InterveneRequest
from backend.services.discussion.service import DiscussionService


def test_should_reject_empty_topic():
    with pytest.raises(ValidationError):
        DiscussionCreateRequest(topic="", character_ids=["x"])


def test_should_reject_duration_below_one_minute():
    with pytest.raises(ValidationError):
        DiscussionCreateRequest(topic="hello", character_ids=["x"], duration=30)


def test_should_reject_empty_intervene():
    with pytest.raises(ValidationError):
        InterveneRequest(content="")


@pytest.mark.asyncio
async def test_should_fallback_topic_when_llm_fails():
    svc = DiscussionService(AsyncMock())
    with pytest.MonkeyPatch.context() as mp:
        def boom(*_a, **_k):
            raise RuntimeError("no llm")

        mp.setattr("backend.services.discussion.service.get_chat_llm", boom)
        result = await svc.generate_topic()
    assert result.source == "fallback"
    assert result.topic


@pytest.mark.asyncio
async def test_should_reject_create_when_skill_not_ready():
    svc = DiscussionService(AsyncMock())
    svc.char_repo = AsyncMock()
    svc.repo = AsyncMock()
    svc.audit = AsyncMock()
    skill = MagicMock()
    skill.status = "generating"
    skill.owner_id = uuid4()
    skill.name = "jobs"
    svc.char_repo.find_by_id.return_value = skill
    owner = str(skill.owner_id)
    req = DiscussionCreateRequest(topic="创新与执行", character_ids=[str(uuid4())])
    with pytest.raises(BusinessException) as exc:
        await svc.create_discussion(owner, req)
    assert exc.value.error_code == ErrorCode.SKILL_NOT_FOUND
    svc.audit.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_record_p1_audit_when_discussion_created():
    svc = DiscussionService(AsyncMock())
    svc.char_repo = AsyncMock()
    svc.repo = AsyncMock()
    svc.audit = AsyncMock()
    owner_id = uuid4()
    skill = MagicMock()
    skill.status = "ready"
    skill.owner_id = owner_id
    skill.name = "jobs"
    svc.char_repo.find_by_id.return_value = skill
    disc = MagicMock()
    disc.id = uuid4()
    disc.owner_id = owner_id
    disc.topic = "创新与执行"
    disc.duration = 600
    disc.status = "pending"
    disc.started_at = None
    disc.ended_at = None
    disc.created_at = MagicMock()
    disc.created_at.isoformat.return_value = "2026-08-16T00:00:00+00:00"
    disc.updated_at = disc.created_at
    svc.repo.create_discussion.return_value = disc
    svc._get_agent_infos = AsyncMock(return_value=[])
    req = DiscussionCreateRequest(topic="创新与执行", character_ids=[str(uuid4())])
    await svc.create_discussion(str(owner_id), req)
    kwargs = svc.audit.record.await_args.kwargs
    assert kwargs["event_type"] == "discussion.create"
    assert kwargs["level"] == "P1"
    assert kwargs["payload"]["topic"] == "创新与执行"
