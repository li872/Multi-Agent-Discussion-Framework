#!/bin/sh
# 审计后端不跑迁移，只启动独立 FastAPI
exec uvicorn audit_backend.main:app --host 0.0.0.0 --port 8001
