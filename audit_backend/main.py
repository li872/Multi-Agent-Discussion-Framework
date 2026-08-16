# 审计后端入口：独立端口，登录态与主系统隔离
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from audit_backend.core.responses import Result
from audit_backend.services.admin_proxy.router import router as admin_proxy_router
from audit_backend.services.auth.router import router as auth_router
from audit_backend.services.events.router import router as events_router

app = FastAPI(title="MADF Audit", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(admin_proxy_router)


@app.get("/api/v1/audit/health")
async def health() -> Result[str]:
    return Result.ok("MADF Audit is running")
