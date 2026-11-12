# Xiaoma

[中文](README.md) | English

Xiaoma is an open-source, free, self-hosted **AI programming learning coach**. It helps beginners truly master programming through structured courses and continuous verification instead of passive reading. The first course is **Python Basics**.

## Features

- **Learning profile & courses** — learning goals, L0/L1/L2 prior knowledge, daily study time; a built-in Python Basics curriculum with chapters, knowledge points and prerequisites.
- **Personalized study plan** — diagnostic form → day-by-day schedule → draft confirmation → versioned adjustments with full history.
- **Daily tasks** — tasks generated from the active plan and current mastery progress; start/complete tracking without duplicate generation.
- **AI teaching** — bring-your-own model, streaming replies, persistent conversations, failed messages marked honestly. All messages are stored locally.
- **LangGraph agent** — a main agent plus Planning / Teaching / Quiz / Review / Resource subgraphs, deterministic intent routing, a service tool layer, overall timeout and error handling, redacted execution logs.
- **Quizzes & mistake review** — seven question types; knowledge-point, chapter and stage quizzes; automatic grading; strict mastery verification; mistake collection with 1/3/7/14-day spaced review. Optional AI variants are validated twice before use.
- **Access protection** — optional access password enforced by the backend middleware; Docker binds to `127.0.0.1` by default; remote binding requires a password and explicit opt-in.
- **Backup & restore** — consistent SQLite snapshots, download/delete backups, automatic pre-restore backup, integrity checks, and a stop-the-service CLI restore flow.
- **Docker Compose** — frontend and backend containers, persistent SQLite volume, health checks, startup ordering, restart policy, automatic migrations and seed data.

V1.0 is single-user and self-hosted. It does **not** execute user-submitted Python code; code questions are analyzed as text only.

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js (App Router) + TypeScript + React |
| Backend | Python 3.14 + FastAPI + SQLAlchemy + Alembic + Pydantic |
| AI | LangGraph + unified LLM provider (DeepSeek, Qwen, OpenAI-compatible endpoints) |
| Database | SQLite |
| Deployment | Docker Compose |

## Quick start (Docker, local only)

Prerequisites: Docker Engine 24+ with Compose v2.24+, network access for the first image build.

```bash
git clone <repository-url> xiaoma
cd xiaoma
cp .env.example .env
docker compose up -d --build
```

Open <http://localhost:3000>.

By default:

- The frontend port is bound to `127.0.0.1` only.
- The backend is **not** published to the host; the browser reaches it through the frontend's same-origin `/api/v1` proxy.
- No password is required, which is safe only for local access.

Check service health:

```bash
docker compose ps
```

Both containers should become `healthy`.

## LAN access (password required)

Edit `.env`:

```dotenv
BIND_ADDRESS=0.0.0.0
XIAOMA_ALLOW_REMOTE=true
XIAOMA_ACCESS_PASSWORD=choose-a-strong-password
```

Then:

```bash
docker compose up -d
```

Open `http://<host-lan-ip>:3000`. The backend refuses to start if the bind address is remote but no password or no explicit remote opt-in is configured.

For public deployments, use an HTTPS reverse proxy and keep the password enabled. See the Chinese [Docker deployment guide](docs/Docker部署指南.md) for details.

## Local development

Backend:

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt        # macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m app.cli init-db
.venv/Scripts/python -m app.cli seed-courses
.venv/Scripts/python -m app.cli seed-questions
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The frontend proxies `/api/v1` to `http://127.0.0.1:8000` via `BACKEND_INTERNAL_URL` (default for local development).

## Model configuration

Open **Settings → Model Configs → Add model**. Supported providers:

| Provider | Base URL | Example model |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Qwen (DashScope compatible mode) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4.1-mini` |
| Custom OpenAI-compatible endpoint | required | provider-specific |

- API keys are encrypted with Fernet before being stored in SQLite; the API and UI only show masked values.
- The encryption key is generated at `data/.secret_key` (inside the Docker volume) unless `XIAOMA_SECRET_KEY` is set. Changing it makes existing keys undecryptable, so re-enter them.
- Without a default model, AI teaching and AI quiz variants are unavailable, but profiles, plans, tasks, built-in quizzes, mistakes and reviews still work.
- Logs never contain full API keys, access passwords, user messages or system prompts.

See [模型配置说明](docs/模型配置说明.md) (Chinese) for full details.

## Data, backup and restore

All data lives in the Docker volume `xiaoma_xiaoma-data` at `/app/data`:

- `xiaoma.db` — profiles, plans, tasks, conversations, quizzes, mistakes and model configs;
- `.secret_key` — API key encryption key;
- `backups/` — database backups.

Create a backup from **Settings → Data backup**, or:

```bash
docker compose exec backend python -m app.cli backup-db
docker compose exec backend python -m app.cli list-backups
```

Restore (stop the backend first; the current database is backed up automatically):

```bash
docker compose stop backend
docker compose run --rm --no-deps backend python -m app.cli restore-db <backup-file-name> --yes
docker compose start backend
```

**Never run `docker compose down -v` unless you intend to delete all data.**

## Security and privacy

- Default deployment is local-only; the backend is not reachable from the host except through the frontend container.
- When a password is configured, every API except health/login/status requires a backend-issued Bearer session token. Protection is enforced by backend middleware, not by hiding UI.
- API keys are encrypted at rest and masked in responses; secrets are never hard-coded.
- `.env` is git-ignored.
- With AI features enabled, prompts and the necessary learning context are sent to **the model provider you configure**. Data is stored in your own deployment and is not uploaded to the Xiaoma developer.

## Testing

```bash
# Backend: unit, API integration, migration and agent workflow tests
cd backend
.venv/Scripts/python -m pytest tests/ -v

# Frontend: core flow tests (Vitest)
cd frontend
npm test
```

## Project structure

```text
.
├── backend/                 # FastAPI application, Alembic migrations, tests
│   ├── app/                 # api / core / services / repositories / agent
│   └── tests/
├── frontend/                # Next.js App Router application and tests
├── docs/                    # PRD, task book, deployment/model/FAQ and progress docs
├── docker-compose.yml
├── .env.example
├── CHANGELOG.md
└── LICENSE
```

## Documentation

Most formal documentation is in Chinese:

- [Product requirements (PRD V1.3)](docs/Xiaoma_PRD_V1.3.md)
- [Docker deployment guide](docs/Docker部署指南.md)
- [Model configuration guide](docs/模型配置说明.md)
- [FAQ](docs/常见问题.md)
- [Development progress and acceptance records](docs/开发进度与验收记录.md)
- [Changelog](CHANGELOG.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
