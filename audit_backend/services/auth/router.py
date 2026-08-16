from fastapi import APIRouter, Depends

from audit_backend import local_db
from audit_backend.core.responses import Result
from audit_backend.deps import create_audit_token, require_audit_admin
from audit_backend.services.auth.schemas import LoginRequest

router = APIRouter(prefix="/api/v1/audit/auth", tags=["audit-auth"])


@router.post("/login")
async def login(req: LoginRequest) -> Result:
    row = local_db.verify_admin(req.username, req.password)
    if not row:
        return Result.fail(1002, "用户名或密码错误")
    token = create_audit_token(row["username"])
    return Result.ok(
        {
            "token": token,
            "admin": {"username": row["username"], "id": row["id"]},
        }
    )


@router.get("/me")
async def me(username: str = Depends(require_audit_admin)) -> Result:
    return Result.ok({"username": username})
