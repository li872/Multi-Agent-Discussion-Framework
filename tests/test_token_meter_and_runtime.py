from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from agent_engine.token_meter import estimate_tokens_from_text, extract_token_count
from backend.services.admin.token_repository import TokenUsageRepository


def test_should_extract_tokens_from_usage_metadata():
    msg = SimpleNamespace(usage_metadata={"total_tokens": 42}, response_metadata={})
    assert extract_token_count(msg) == 42


def test_should_extract_tokens_from_response_metadata():
    msg = SimpleNamespace(
        usage_metadata=None,
        response_metadata={"token_usage": {"prompt_tokens": 10, "completion_tokens": 5}},
    )
    assert extract_token_count(msg) == 15


def test_should_estimate_tokens_from_text():
    assert estimate_tokens_from_text("abcd") == 1
    assert estimate_tokens_from_text("a" * 40) == 10


@pytest.mark.asyncio
async def test_should_record_token_usage_row():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    repo = TokenUsageRepository(session)
    uid = uuid4()
    did = uuid4()
    row = await repo.record(tokens=12, user_id=uid, discussion_id=did, kind="agent_speak")
    session.add.assert_called_once()
    assert row.tokens == 12
    assert row.user_id == uid
    assert row.discussion_id == did
    assert row.kind == "agent_speak"
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_should_track_orchestrator_task_in_registry():
    from backend.services.discussion import service as disc_svc

    disc_svc._active_orchestrators.clear()
    did = uuid4()

    async def _noop(**_kwargs):
        return None

    with patch.object(disc_svc, "run_multi_discussion", _noop):
        await disc_svc._start_orchestrator(
            discussion_id=did,
            topic="t",
            duration=60,
            agents=[],
            owner_id=uuid4(),
        )
        assert str(did) in disc_svc._active_orchestrators
        task = disc_svc._active_orchestrators[str(did)]
        await task
        assert str(did) not in disc_svc._active_orchestrators


@pytest.mark.asyncio
async def test_should_write_error_audit_with_owner_on_crash():
    from agent_engine.discussion import multi_orchestrator as mo
    from agent_engine.discussion.multi_orchestrator import AgentSpec, run_multi_discussion

    did = uuid4()
    owner = uuid4()
    disc = MagicMock()
    disc.id = did

    repo = AsyncMock()
    repo.find_by_id.return_value = disc
    repo.update_status = AsyncMock()
    repo.list_messages.return_value = []

    audit = AsyncMock()

    class _CM:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *args):
            return False

    def session_factory():
        return _CM()

    with (
        patch.object(mo, "async_session_factory", side_effect=[_CM(), _CM()]),
        patch.object(mo, "DiscussionRepository", return_value=repo),
        patch.object(mo, "AuditRepository", return_value=audit),
        patch.object(mo, "get_chat_llm", side_effect=RuntimeError("boom")),
        patch.object(mo, "_publish_status", AsyncMock()),
        patch.object(mo, "publish_discussion_event", AsyncMock()),
        patch.object(mo, "create_roundtable_agent", side_effect=Exception("skip")),
        patch.object(mo, "_read_skill_excerpt", return_value=""),
    ):
        # first session for main run, second for error path — simplify by making factory always return same session mock
        pass

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.commit = AsyncMock()

    with (
        patch.object(mo, "async_session_factory", return_value=session),
        patch.object(mo, "DiscussionRepository", return_value=repo),
        patch.object(mo, "AuditRepository", return_value=audit),
        patch.object(mo, "get_chat_llm", side_effect=RuntimeError("boom")),
        patch.object(mo, "_publish_status", AsyncMock()) as pub_status,
        patch.object(mo, "publish_discussion_event", AsyncMock()),
        patch.object(mo, "create_roundtable_agent", side_effect=Exception("skip")),
        patch.object(mo, "_read_skill_excerpt", return_value=""),
    ):
        await run_multi_discussion(
            discussion_id=did,
            topic="crash topic",
            duration=60,
            agents=[
                AgentSpec(agent_id=uuid4(), agent_name="Ada", skill_file_path="x/y")
            ],
            owner_id=owner,
        )

    audit.record.assert_awaited()
    kwargs = audit.record.await_args.kwargs
    assert kwargs["event_type"] == "discussion.error"
    assert kwargs["level"] == "P1"
    assert kwargs["user_id"] == owner
    assert kwargs["discussion_id"] == did
    repo.update_status.assert_awaited()
    pub_status.assert_awaited()
