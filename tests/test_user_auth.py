from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.core.exceptions import BusinessException, ErrorCode
from backend.services.user.schemas import UserLoginRequest, UserRegisterRequest
from backend.services.user.service import UserService


def test_should_reject_short_password_on_register():
    with pytest.raises(ValidationError):
        UserRegisterRequest(username="ab", password="123")


def test_should_reject_short_username_on_login():
    with pytest.raises(ValidationError):
        UserLoginRequest(username="a", password="secret1")


def _svc() -> UserService:
    session = AsyncMock()
    svc = UserService(session)
    svc.repo = AsyncMock()
    svc.audit = AsyncMock()
    return svc


def _user(*, username="alice"):
    u = MagicMock()
    u.id = uuid4()
    u.username = username
    u.phone = None
    u.password_hash = UserService(AsyncMock()).pwd_context.hash("secret1")
    u.created_at = datetime.now(timezone.utc)
    return u


@pytest.mark.asyncio
async def test_should_raise_username_exists_when_register_duplicate():
    svc = _svc()
    svc.repo.find_by_username.return_value = MagicMock()
    with pytest.raises(BusinessException) as exc:
        await svc.register("alice", "secret1", None)
    assert exc.value.error_code == ErrorCode.USERNAME_EXISTS


@pytest.mark.asyncio
async def test_should_audit_p0_when_login_user_missing():
    svc = _svc()
    svc.repo.find_by_username.return_value = None
    with pytest.raises(BusinessException) as exc:
        await svc.login("ghost", "secret1")
    assert exc.value.error_code == ErrorCode.USER_NOT_FOUND
    kwargs = svc.audit.record.await_args.kwargs
    assert kwargs["event_type"] == "user.login_failed"
    assert kwargs["level"] == "P0"
    assert kwargs["payload"]["reason"] == "user_not_found"


@pytest.mark.asyncio
async def test_should_audit_wrong_password_when_login_fails():
    svc = _svc()
    user = _user()
    svc.repo.find_by_username.return_value = user
    with pytest.raises(BusinessException) as exc:
        await svc.login("alice", "badpass")
    assert exc.value.error_code == ErrorCode.WRONG_PASSWORD
    kwargs = svc.audit.record.await_args.kwargs
    assert kwargs["payload"]["reason"] == "wrong_password"
    assert kwargs["user_id"] == user.id


@pytest.mark.asyncio
async def test_should_issue_jwt_and_audit_when_login_ok():
    svc = _svc()
    user = _user()
    svc.repo.find_by_username.return_value = user
    token, resp = await svc.login("alice", "secret1")
    assert token.token
    assert resp.username == "alice"
    kwargs = svc.audit.record.await_args.kwargs
    assert kwargs["event_type"] == "user.login"
    assert kwargs["level"] == "P0"
    assert kwargs["user_id"] == user.id
