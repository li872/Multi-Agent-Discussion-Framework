# Multi-Agent Discussion Framework
多智能体圆桌讨论平台。用户选择 AI 角色，给出话题，角色们自发讨论——每轮由置信度最高的 Agent 抢到发言权，流式输出，用户可随时插话。

## 技术栈

| 层 | 选型 |
|---|------|
| 后端 | FastAPI + Python 3.12 |
| 数据库 | PostgreSQL |
| 缓存/消息 | Redis |
| Agent 框架 | LangGraph |
| 前端 | React + Tailwind CSS |
| 部署 | Docker Compose |

## 项目结构
backend/        FastAPI 应用
agent_engine/   Agent 核心逻辑
audit_backend/  审计管理后台
frontend/       React 前端
alembic/        数据库迁移
tests/          测试

## 启动方式
docker compose up -d
