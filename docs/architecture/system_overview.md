# System Overview

## Technology Validation

### Backend Technologies

| Technology | Status | Evidence (Source Code) |
|---|---|---|
| FastAPI | VERIFIED | `backend/main.py`: `from fastapi import FastAPI`; route decorators throughout `broker/api/` |
| Python 3.10 | VERIFIED | venv at `backend/.venv/lib/python3.10/` |
| SQLAlchemy 2.x (async) | VERIFIED | `backend/persistence/database_async.py`: `from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession` |
| MySQL | VERIFIED | `backend/core/config/settings.py`: `DatabaseSettings.url` returns `mysql+pymysql://...`; `async_url` returns `mysql+asyncmy://...` |
| asyncmy | VERIFIED | `backend/core/config/settings.py`: `async_url` property uses `mysql+asyncmy://` driver string |
| PyMySQL | VERIFIED | `backend/core/config/settings.py`: `url` property uses `mysql+pymysql://` driver string |
| Redis (async) | VERIFIED | `backend/shared/utils/redis_client.py`: `import redis.asyncio as aioredis`; `RedisClient` class |
| Pydantic v2 + pydantic-settings | VERIFIED | `backend/core/config/settings.py`: `from pydantic_settings import BaseSettings, SettingsConfigDict` |
| Alembic | VERIFIED | `backend/persistence/migrations/versions/` — 20+ migration files |
| PyJWT | VERIFIED | `backend/core/security/jwt.py`: `import jwt`; `jwt.encode(...)` and `jwt.decode(...)` |
| passlib + bcrypt | VERIFIED | `backend/core/security/password.py` (referenced from `service_async.py`): `from core.security.password import hash_password, verify_password` |
| uvicorn + uvloop | VERIFIED | `requirements.txt` listed; production systemd service invokes uvicorn |
| APScheduler (AsyncIO) | VERIFIED | `backend/core/stats/scheduler.py`: `from apscheduler.schedulers.asyncio import AsyncIOScheduler` |
| slowapi | PARTIALLY USED | In `requirements.txt`; not observed applied to routes in reviewed code |
| python-socketio | NOT FOUND IN CODE | In `requirements.txt`; `broker/api/routes.py` has `# TODO: Include realtime routes` comment; no active socketio routes |
| openpyxl | VERIFIED | `backend/features/quiz/import_service.py`: `import openpyxl` |
| wordcloud + Pillow | VERIFIED | `backend/features/quiz/export_service.py`: `from wordcloud import WordCloud` |
| reportlab | VERIFIED | `backend/features/quiz/export_service.py`: pdf export via reportlab |
| python-docx | VERIFIED | `backend/features/quiz/export_service.py`: docx export |
| python-pptx | VERIFIED | `backend/features/quiz/export_service.py`: pptx export |
| Locust | VERIFIED | `locustfile.py`: `from locust import HttpUser, task` |
| pytest | VERIFIED | Test files in `backend/` use pytest |

### Frontend Technologies

| Technology | Status | Evidence (Source Code) |
|---|---|---|
| React 18 | VERIFIED | `frontend/src/main.jsx`: root render; `App.jsx` uses React hooks |
| Vite 5 | VERIFIED | `frontend/vite.config.js` and `package.json` scripts |
| Ant Design 5 | VERIFIED | `frontend/src/App.jsx`: `from 'antd'` imports; ConfigProvider, Button, Tag, etc. |
| @ant-design/pro-components + pro-layout | VERIFIED | `frontend/src/App.jsx`: `import { ProLayout } from '@ant-design/pro-components'` |
| Redux Toolkit | VERIFIED | `frontend/src/store/store.js`: `configureStore`; `frontend/src/store/authSlice.js`: `createSlice` |
| React Router v6 | VERIFIED | `frontend/src/App.jsx`: `import { BrowserRouter, Routes, Route, Navigate }` |
| Axios | VERIFIED | `frontend/src/services/api.js`: `import axios from 'axios'`; `axios.create({...})` |
| react-i18next / i18next | VERIFIED | `frontend/src/App.jsx`: `import { useTranslation } from 'react-i18next'` |
| Tiptap (rich text editor) | VERIFIED | Referenced in quiz question editor components |
| Recharts | VERIFIED | `frontend/src/features/admin/Statistics.jsx` |
| D3 + d3-cloud | VERIFIED | `package.json` |
| react-wordcloud | VERIFIED | `frontend/src/features/audience/AudienceSession.jsx` |
| @mediapipe/tasks-vision | VERIFIED | `frontend/src/features/proctoring/hooks/useFaceDetector.js`: `import('@mediapipe/tasks-vision')` dynamic import |
| qrcode.react | VERIFIED | Used in session control/join UI |
| xlsx | VERIFIED | Imported in admin export flows |
| Bootstrap 5 | PARTIALLY USED | In `package.json`; not dominant — Ant Design is primary UI framework |

### Infrastructure

| Technology | Status | Evidence (Source Code) |
|---|---|---|
| Nginx | VERIFIED | `main.py`: uploads mounted at `/api/uploads`; production config references `/frontend/dist` |
| Selenium + Chromium | VERIFIED | `test_*_selenium.py` files in repo |
| Docker | VERIFIED | Selenium container usage via `sudo docker` in test scripts |

### Technologies in Code NOT Listed in TechnologiesUsed.md

| Technology | Evidence |
|---|---|
| fastapi-mail | `backend/core/auth/email_service.py`: `from fastapi_mail import FastMail, MessageSchema, ConnectionConfig` |
| httpx | `backend/core/ai/ollama_service.py`: `import httpx`; `backend/broker/api/auth.py` Google OAuth uses `httpx.AsyncClient` |
| Ollama (local LLM daemon) | `backend/core/ai/ollama_service.py`: HTTP calls to `http://127.0.0.1:11434`; default model `qwen2.5:3b` |
| dayjs | `frontend/src/features/exam/ExamSession.jsx`: `import dayjs` |

---

## System Behavior (Code-Derived)

### Application Startup Sequence

Defined in `backend/main.py`, `lifespan()` async context manager:

1. `await redis_client.connect()` — Redis pool initialized (`shared/utils/redis_client.py`)
2. Uploads and temp directories created at `/home/vinay/Swaya.me/backend/uploads/images` and `.../temp`
3. `ImageService.cleanup_old_temp_files(max_age_hours=2)` — stale temp files removed
4. `start_scheduler()` — APScheduler started with hourly and daily snapshot jobs (`core/stats/scheduler.py`)
5. `seed_platform_rules(seed_db)` — proctoring rules seeded into DB (`features/proctoring/rule_registry.py`)

On shutdown: scheduler stopped, Redis disconnected.

### Middleware Stack (Applied Order)

1. **CORSMiddleware** — origins from `settings.app.allowed_origins`
2. **TrustedHostMiddleware** — active only when `settings.app.debug == False`; allows `*.swaya.me` and `localhost`
3. **tenant_isolation_middleware** (`broker/policies/tenant_isolation.py`) — extracts `tenant_id` from JWT into request-scoped `TenantContext`

### API Prefix

All API routes: `/api/v1/...`
Static uploads: `/api/uploads/...`
Health check: `/health` (root level)

---

## Subsystems and Responsibilities

### Auth (`broker/api/auth.py`, `core/auth/`)
- Registration: creates Tenant + User + starter demo quiz atomically
- Login: validates password, checks email verification, generates JWT (HS256, 24h TTL)
- Google OAuth: exchanges auth code via httpx, links or creates user
- Password reset: token-based, 1-hour expiry
- Email: fastapi-mail via SMTP (titan.email configured); logs-only fallback if SMTP unconfigured

### Quiz Management (`broker/api/quiz.py`, `features/quiz/`)
- CRUD for quizzes: create/update/delete/duplicate/publish (status: DRAFT → READY)
- Question management: add/update/delete/reorder within draft quizzes
- Quiz types: QUIZ, POLL, OFFLINE_POLL, EXAM
- Folder system: nested folders scoped per tenant
- Template system: global or tenant-scoped quiz templates
- Excel import/export: `features/quiz/import_service.py`, `export_service.py`

### Live Session Management (`features/quiz/session_service_async.py`)
- Start session: checks tier limits (concurrent events), creates QuizSession record, writes audience state to Redis
- Join session: creates Participant with unique `session_token`, caches token→participant in Redis
- Advance/back question: updates `current_question_index`, writes new audience state cache
- Answer submission: validates question is OPEN, checks for duplicates, writes answer to DB and Redis counters
- Whiteboard state: stored in Redis, streamed via SSE endpoint

### Exam (`broker/api/exam.py`, `features/quiz/exam_service_async.py`)
- Public slug-based access: `/e/{slug}`
- Self-paced: participants start, save individual answers, then submit
- Auto-scoring: MCQ correct answer comparison at submit time
- Time limit enforced on frontend (NOT server-side gated)

### Offline Poll (`broker/api/offline_poll.py`, `features/quiz/offline_poll_service_async.py`)
- Public slug-based: `/poll/{slug}`
- No live host required; open/close window defined by `offline_start_at`/`offline_end_at`
- Results accessible to authenticated host only

### Proctoring (`broker/api/proctoring.py`, `features/proctoring/`)
- Rule resolution: platform rules → tenant policy overrides → quiz-level policy
- Redis-cached rule sets per quiz (1-hour TTL)
- Violation tracking: in-memory counters in Redis, persisted to `proctoring_events` table
- Lock escalation: immediate lock on specific events (MULTI_TAB, honeypot hits); threshold-based for others
- Webcam monitoring: frontend-only via MediaPipe BlazeFace (not server-side video analysis)
- Snapshots: uploaded to `/uploads/proctoring/{quiz_id}/{participant_id}/`

### AI Generation (`broker/api/ai.py`, `core/ai/ollama_service.py`)
- Local Ollama daemon at `127.0.0.1:11434`
- Default model: `qwen2.5:3b`; fallback: `llama3.2:1b`
- Functions: generate MCQ questions, generate distractors, generate poll prompts, rewrite text
- Restricted to `admin` and `super_admin` roles (except rewrite which requires any authenticated user)

### Statistics (`broker/api/stats.py`, `core/stats/`)
- APScheduler captures hourly and daily snapshots to `stats_snapshots` table
- Snapshots scoped at PLATFORM or TENANT level
- History queryable via `/admin/stats/history`

### Tier Enforcement (`core/config/tier_service.py`)
- Limits: max_participants, max_questions, max_concurrent_events
- DB config in `tier_configurations` table; Redis-cached with 5-minute TTL
- Hard-coded defaults if DB row missing (FREE: 50 participants, 10 questions, 1 event)

---

## High-Level Request/Data Flow

### Authenticated Host Request
```
Browser → Nginx → uvicorn (port 8000/8001)
  → FastAPI middleware stack (CORS → TrustedHost → tenant_isolation)
  → api_router (/api/v1/...)
  → route handler (broker/api/*.py)
  → get_current_user() dependency: JWT decode → DB fetch User+Tenant
  → service function (features/quiz/*_service_async.py)
  → AsyncSession → MySQL (asyncmy)
  → Redis (for caches/counters)
  → Pydantic response model → JSON
```

### Participant (Anonymous) Request
```
Browser → Nginx → uvicorn
  → FastAPI middleware
  → route handler (no auth dependency)
  → service function
  → session_token lookup: Redis first (fast path), DB fallback
  → MySQL / Redis
  → JSON response
```
