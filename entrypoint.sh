#!/bin/sh
# 后端容器入口：先执行 Alembic 迁移，再启动 uvicorn
# 依赖：postgres 服务已 healthy（由 docker-compose depends_on 保证）

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
