from fastapi import FastAPI

from backend.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/api/v1/health")
async def health():
    return {"code": 200, "message": "success", "data": f"{settings.app_name} is running"}