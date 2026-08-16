from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from audit_backend.core.responses import Result
from audit_backend.deps import require_audit_admin
from audit_backend import local_db

router = APIRouter(prefix="/api/v1/audit/admins", tags=["audit-admins"])


class AdminCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class AdminUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=64)
    password: str | None = Field(default=None, min_length=6, max_length=128)


@router.get("/")
async def list_admins(_: str = Depends(require_audit_admin)) -> Result:
    return Result.ok({"items": local_db.list_admins()})


@router.post("/")
async def create_admin(body: AdminCreate, _: str = Depends(require_audit_admin)) -> Result:
    if local_db.find_admin(body.username):
        raise HTTPException(status_code=409, detail="Username exists")
    return Result.ok(local_db.create_admin(body.username, body.password))


@router.put("/{admin_id}")
async def update_admin(
    admin_id: str, body: AdminUpdate, _: str = Depends(require_audit_admin)
) -> Result:
    row = local_db.update_admin(admin_id, username=body.username, password=body.password)
    if not row:
        raise HTTPException(status_code=404, detail="Admin not found")
    return Result.ok(row)


@router.delete("/{admin_id}")
async def delete_admin(admin_id: str, _: str = Depends(require_audit_admin)) -> Result:
    if not local_db.delete_admin(admin_id):
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    return Result.ok({"id": admin_id, "ok": True})
