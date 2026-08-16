from uuid import uuid4

from fastapi import HTTPException
import pytest

from audit_backend.deps import create_audit_token
from audit_backend.config import settings as audit_settings
from backend.config import settings
from backend.services.admin.router import _require_admin_token
from backend.services.admin.service import AdminService
from backend.services.audit.repository import AuditRepository
from jose import jwt
from unittest.mock import AsyncMock, MagicMock


def test_should_convert_uuid_strings_in_audit_repo():
    repo = AuditRepository(None)  # type: ignore[arg-type]
    uid = uuid4()
    assert repo._to_uuid(None) is None
    assert repo._to_uuid(uid) == uid
    assert repo._to_uuid(str(uid)) == uid


def test_should_reject_admin_request_without_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "ops-secret")
    with pytest.raises(HTTPException) as exc:
        _require_admin_token(None)
    assert exc.value.status_code == 403


def test_should_accept_matching_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "ops-secret")
    assert _require_admin_token("ops-secret") is None


def test_should_reject_empty_admin_token_config(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "")
    with pytest.raises(HTTPException) as exc:
        _require_admin_token("anything")
    assert exc.value.status_code == 403


def test_should_encode_audit_audience_in_jwt():
    token = create_audit_token("admin")
    payload = jwt.decode(
        token,
        audit_settings.audit_jwt_secret,
        algorithms=[audit_settings.jwt_algorithm],
        audience="audit",
    )
    assert payload["sub"] == "admin"
    assert payload["aud"] == "audit"


@pytest.mark.asyncio
async def test_should_write_p0_audit_when_admin_disables_user():
    session = AsyncMock()
    svc = AdminService(session)
    svc.users = AsyncMock()
    svc.audit = AsyncMock()
    user = MagicMock()
    user.id = uuid4()
    user.username = "bob"
    user.phone = None
    user.deleted_at = None
    user.created_at = MagicMock()
    user.created_at.isoformat.return_value = "2026-08-16T00:00:00+00:00"
    svc.users.find_by_id_any.return_value = user
    await svc.set_user_status(str(user.id), False)
    kwargs = svc.audit.record.await_args.kwargs
    assert kwargs["event_type"] == "user.status_changed"
    assert kwargs["level"] == "P0"
    assert kwargs["payload"]["status"] == "disabled"
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_should_write_p1_audit_when_admin_deletes_discussion():
    session = AsyncMock()
    svc = AdminService(session)
    svc.discussions = AsyncMock()
    svc.audit = AsyncMock()
    disc = MagicMock()
    disc.id = uuid4()
    disc.topic = "圆桌"
    svc.discussions.find_by_id.return_value = disc
    await svc.delete_discussion(str(disc.id))
    kwargs = svc.audit.record.await_args.kwargs
    assert kwargs["event_type"] == "discussion.deleted_by_admin"
    assert kwargs["level"] == "P1"
    assert kwargs["discussion_id"] == disc.id


@pytest.mark.asyncio
async def test_should_write_p1_audit_when_admin_unlists_character():
    session = AsyncMock()
    svc = AdminService(session)
    svc.characters = AsyncMock()
    svc.audit = AsyncMock()
    skill = MagicMock()
    skill.id = uuid4()
    skill.name = "jobs"
    svc.characters.find_by_id.return_value = skill
    await svc.set_character_visibility(str(skill.id), False)
    kwargs = svc.audit.record.await_args.kwargs
    assert kwargs["event_type"] == "skill.visibility_changed"
    assert kwargs["level"] == "P1"
    assert kwargs["payload"]["is_public"] is False


@pytest.mark.asyncio
async def test_should_write_p1_audit_when_admin_deletes_character():
    session = AsyncMock()
    svc = AdminService(session)
    svc.characters = AsyncMock()
    svc.audit = AsyncMock()
    skill = MagicMock()
    skill.id = uuid4()
    skill.name = "jobs"
    svc.characters.find_by_id.return_value = skill
    await svc.delete_character(str(skill.id))
    kwargs = svc.audit.record.await_args.kwargs
    assert kwargs["event_type"] == "character.deleted_by_admin"
    assert kwargs["level"] == "P1"
    assert kwargs["payload"]["skill_name"] == "jobs"
