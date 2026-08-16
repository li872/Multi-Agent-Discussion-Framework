# 后端 FastAPI 容器
# 技术：Python 3.12 + uvicorn + 项目 pyproject.toml 依赖
# 基础镜像已预先从 DaoCloud 镜像源拉取到本地并 retag 为官方名称
FROM python:3.12-slim

WORKDIR /app

# 先复制依赖描述，利用 Docker cache
COPY pyproject.toml ./
COPY backend ./backend
COPY agent_engine ./agent_engine
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# 安装项目及其依赖（editable，方便调试）
RUN pip install --no-cache-dir -e "."

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
