# 后端 FastAPI 容器
# 技术：Python 3.12 + uvicorn + 项目 pyproject.toml 依赖
# 使用阿里云镜像源，避免国内拉取 docker.io 官方镜像失败
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.12-slim

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
