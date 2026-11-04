# 审计后端入口：独立端口，登录态与主系统隔离
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from audit_backend import local_db
from audit_backend.config import settings
from audit_backend.core.responses import Result
from audit_backend.services.admin_proxy.router import router as admin_proxy_router
from audit_backend.services.admins.router import router as admins_router
from audit_backend.services.auth.router import router as auth_router
from audit_backend.services.events.router import router as events_router
from audit_backend.services.realtime.router import router as listen_router
from audit_backend.services.settings.router import router as settings_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    local_db.init_db()
    yield


app = FastAPI(title="MADF Audit", version="0.1.0", lifespan=lifespan)
# 默认不开放任何跨域来源：前端经 nginx 同源反代访问，无需 CORS；
# 如需跨域部署，在 .env 用 AUDIT_CORS_ORIGINS 显式列出
_cors_origins = [o.strip() for o in settings.audit_cors_origins.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(admins_router)
app.include_router(settings_router)
app.include_router(listen_router)
app.include_router(admin_proxy_router)


@app.get("/api/v1/audit/health")
async def health() -> Result[str]:
    return Result.ok("MADF Audit is running")
