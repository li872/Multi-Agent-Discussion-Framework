from fastapi import FastAPI

from backend.config import settings
from backend.core.exception_handlers import register_exception_handlers
from backend.core.responses import Result
from backend.services.admin import router as admin_router
from backend.services.character.router import router as character_router
from backend.services.discussion.router import router as discussion_router
from backend.services.user.router import router as user_router
from backend.services.realtime.router import router as realtime_router

app = FastAPI(title=settings.app_name, version="0.1.0")
register_exception_handlers(app)
app.include_router(user_router)
app.include_router(character_router)
app.include_router(discussion_router)
app.include_router(realtime_router)
app.include_router(admin_router)


@app.get("/api/v1/health")
async def health() -> Result[str]:
    return Result.ok(f"{settings.app_name} is running")