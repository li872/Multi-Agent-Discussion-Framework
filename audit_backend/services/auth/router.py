from fastapi import APIRouter, Depends

from audit_backend.config import settings
from audit_backend.core.responses import Result
from audit_backend.deps import create_audit_token, require_audit_admin
from audit_backend.services.auth.schemas import LoginRequest

router = APIRouter(prefix="/api/v1/audit/auth", tags=["audit-auth"])


@router.post("/login")
async def login(req: LoginRequest) -> Result:
    # 一期用环境变量里的审计员账号，不建独立管理员表
    if (
        req.username != settings.audit_admin_username
        or req.password != settings.audit_admin_password
    ):
        return Result.fail(1002, "用户名或密码错误")
    token = create_audit_token(req.username)
    return Result.ok(
        {
            "token": token,
            "admin": {"username": req.username},
        }
    )


@router.get("/me")
async def me(username: str = Depends(require_audit_admin)) -> Result:
    return Result.ok({"username": username})
