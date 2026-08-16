from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from audit_backend.core.responses import Result
from audit_backend.deps import require_audit_admin
from audit_backend import local_db

router = APIRouter(prefix="/api/v1/audit/settings", tags=["audit-settings"])


class RetentionBody(BaseModel):
    days: int = Field(ge=1, le=3650)


@router.get("")
async def get_settings(_: str = Depends(require_audit_admin)) -> Result:
    return Result.ok(local_db.get_settings())


@router.put("/retention")
async def set_retention(
    body: RetentionBody, _: str = Depends(require_audit_admin)
) -> Result:
    return Result.ok(local_db.set_retention_days(body.days))


@router.post("/restart")
async def restart(_: str = Depends(require_audit_admin)) -> Result:
    return Result.ok(
        {"ok": True, "message": "请在服务器执行 docker compose restart 使端口等配置生效"}
    )
