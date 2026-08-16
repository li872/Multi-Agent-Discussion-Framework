# 审计员 JWT：存在 localStorage.audit_token，不能当主系统 token 用
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from audit_backend.config import settings

security_scheme = HTTPBearer(auto_error=False)


def create_audit_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": username, "aud": "audit", "exp": expire},
        settings.audit_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


async def require_audit_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.audit_jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="audit",
        )
        username = payload.get("sub") or ""
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
