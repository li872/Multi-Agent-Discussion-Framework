# MADF — Multi-Agent Discussion Framework

MADF is an open-source multi-agent roundtable discussion platform. Pick a topic, assign LLM-powered roles, and watch them debate in real time — with the ability to jump in and steer the conversation at any moment.

## Features

- **Multi-agent roundtable discussion** — several LLM roles debate one topic under a facilitator that arbitrates decisions and turn order
- **Real-time streaming** — discussion transcripts stream live over SSE
- **Human-in-the-loop** — intervene at any point: pause, redirect, or inject new instructions mid-discussion
- **Role management** — generate and manage discussion characters, each with its own persona and perspective
- **Independent audit console** — a separate admin backend that records operation logs, LLM token usage, and discussion lifecycle events, protected by its own JWT auth
- **One-command deployment** — full stack runs via Docker Compose; CI covers unit, integration, frontend, E2E and Docker smoke tests

## Architecture

| Service | Stack | Port |
| --- | --- | --- |
| `frontend` | React + Vite, served by nginx | 80 |
| `backend` | FastAPI + PostgreSQL + Redis | 8000 |
| `audit-backend` | FastAPI + SQLite (independent auth) | 8001 |
| `audit-frontend` | React + Vite, served by nginx | 81 |

The backend exposes routers for users, characters, discussions, realtime (SSE) and admin. `agent_engine` hosts the multi-agent orchestration logic, including a distilled skill engine for generating discussion personas. Database migrations use Alembic.

The two frontends talk to their APIs through same-origin nginx reverse proxies, so no cross-origin requests are needed in the default deployment.

## Quick Start

```bash
cp env.template .env
# edit .env: set LLM_API_KEY (and AUDIT_ADMIN_* — see below)
docker compose up -d
```

Then open:

- Main app: http://localhost
- Audit console: http://localhost:81

### First audit admin

On first start, the audit backend seeds an initial administrator from `AUDIT_ADMIN_USERNAME` / `AUDIT_ADMIN_PASSWORD` (stored as a bcrypt hash). These variables **must** be set before first launch; the service refuses to start seeding without them. After seeding, credentials live in the database — changing the env vars later does not change existing accounts. Use the admin console to manage further accounts.

## Configuration

| Variable | Purpose |
| --- | --- |
| `LLM_API_KEY` / `LLM_API_BASE` / `LLM_MODEL` | Any OpenAI-compatible chat API (DeepSeek, OpenAI, local servers, ...) |
| `TAVILY_API_KEY` | Optional, used by full role generation |
| `JWT_SECRET` | Main backend JWT signing secret |
| `ADMIN_JWT_SECRET` | Admin JWT signing secret |
| `AUDIT_JWT_SECRET` | Audit backend JWT signing secret |
| `AUDIT_ADMIN_USERNAME` / `AUDIT_ADMIN_PASSWORD` | First audit admin bootstrap credentials (required) |
| `AUDIT_CORS_ORIGINS` | Comma-separated cross-origin allowlist; empty = same-origin only |
| `DB_*` / `REDIS_*` | PostgreSQL / Redis connection settings |

Keep `.env` out of version control — it is already listed in `.gitignore`.

## Testing

```bash
pytest tests/            # Python unit + integration tests
cd frontend && npm test  # vitest
npx playwright test      # E2E
```

CI runs ruff lint, the full test matrix and a Docker smoke boot on every push.

## Contributing

Issues and pull requests are welcome — including new discussion orchestration strategies, audit metrics and docs improvements.
