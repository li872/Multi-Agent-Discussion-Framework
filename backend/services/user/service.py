# 注册/登录规则 + bcrypt + JWT
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
from backend.services.user.repository import UserRepository
from backend.services.user.schemas import TokenResponse, UserResponse, UserUpdateRequest


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def register(
        self, username: str, password: str, phone: str | None
    ) -> tuple[TokenResponse, UserResponse]:
        existing = await self.repo.find_by_username(username)
        if existing:
            raise BusinessException(
                ErrorCode.USERNAME_EXISTS,
                f"Username '{username}' already taken",
            )

        if phone:
            existing_phone = await self.repo.find_by_phone(phone)
            if existing_phone:
                raise BusinessException(
                    ErrorCode.PHONE_EXISTS,
                    f"Phone '{phone}' already registered",
                )

        password_hash = self.pwd_context.hash(password)
        user = await self.repo.create(username, password_hash, phone)
        token = self._issue_token(user.id)
        return token, self._to_response(user)

    async def login(
        self, username: str, password: str
    ) -> tuple[TokenResponse, UserResponse]:
        user = await self.repo.find_by_username(username)
        if not user:
            raise BusinessException(
                ErrorCode.USER_NOT_FOUND,
                "Invalid username or password",
            )

        if not self.pwd_context.verify(password, user.password_hash):
            raise BusinessException(
                ErrorCode.WRONG_PASSWORD,
                "Invalid username or password",
            )

        token = self._issue_token(user.id)
        return token, self._to_response(user)

    async def get_me(self, user_id: str) -> UserResponse:
        user = await self.repo.find_by_id(uuid.UUID(user_id))
        if not user:
            raise BusinessException(ErrorCode.USER_NOT_FOUND)
        return self._to_response(user)

    async def update_me(self, user_id: str, req: UserUpdateRequest) -> UserResponse:
        # 更新当前用户信息：用户名、手机号、密码（旧密码校验）
        user = await self.repo.find_by_id(uuid.UUID(user_id))
        if not user:
            raise BusinessException(ErrorCode.USER_NOT_FOUND)

        changed = False

        if req.username is not None and req.username != user.username:
            existing = await self.repo.find_by_username(req.username)
            if existing and str(existing.id) != user_id:
                raise BusinessException(
                    ErrorCode.USERNAME_EXISTS, "Username already taken"
                )
            user.username = req.username
            changed = True

        if req.phone is not None and req.phone != user.phone:
            existing_phone = await self.repo.find_by_phone(req.phone)
            if existing_phone and str(existing_phone.id) != user_id:
                raise BusinessException(
                    ErrorCode.PHONE_EXISTS, "Phone already registered"
                )
            user.phone = req.phone
            changed = True

        if req.new_password:
            if not req.old_password:
                raise BusinessException(
                    ErrorCode.INVALID_PARAMS, "Old password required to change password"
                )
            if not self.pwd_context.verify(req.old_password, user.password_hash):
                raise BusinessException(
                    ErrorCode.WRONG_PASSWORD, "Incorrect old password"
                )
            user.password_hash = self.pwd_context.hash(req.new_password)
            changed = True

        if changed:
            user = await self.repo.update(user)

        return self._to_response(user)

    def _issue_token(self, user_id: uuid.UUID) -> TokenResponse:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )
        payload = {"sub": str(user_id), "exp": expire}
        token = jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        return TokenResponse(token=token)

    @staticmethod
    def _to_response(user) -> UserResponse:
        return UserResponse(
            id=str(user.id),
            username=user.username,
            phone=user.phone,
            created_at=user.created_at.isoformat(),
        )


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)