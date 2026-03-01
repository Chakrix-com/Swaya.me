# Swaya.me — Claude Code Guide

## Project Overview

**Swaya.me** is a multi-tenant interactive quiz/audience engagement platform. Hosts create and run live quiz sessions; audience members join anonymously via a join code.

Key capabilities:
- Quiz builder (MCQ + Word Cloud question types, optional images)
- Live session control (advance/back/end questions)
- Real-time audience participation (no login required)
- Tier-based quotas (FREE / BASIC / PRO / ENTERPRISE)
- Multi-language UI (en, hi, ta, te, ka, bn, gu via react-i18next)
- Admin panel (users, orgs, stats, feedback, platform quizzes, tier config)

---

## Deployment & Infrastructure

- **Production domain**: `www.swaya.me` (also `swaya.me`)
- **Web server**: Nginx — serves the frontend from `~/frontend/dist`
- **Server management**: aaPanel (not Docker for production services)
- **Docker**: Used ONLY for Selenium/ARM screen testing (`seleniumarm`)
- **Platform**: Single OCI IaaS Linux VM (Oracle Cloud)
- **Backend runtime**: Python 3.10 virtualenv at `backend/.venv`

### Frontend build & deploy
```bash
cd frontend && npm run build   # outputs to frontend/dist
# Nginx picks up frontend/dist automatically
```

### Backend start (via aaPanel / systemd)
The backend runs with uvicorn:
```bash
cd backend && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```
Config is in `backend/.env` (not committed).

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.104.1 |
| Runtime | Python 3.10, uvicorn |
| DB ORM | SQLAlchemy 2.0 (async + sync) |
| Database | MySQL (via asyncmy / PyMySQL) |
| Migrations | Alembic |
| Cache/State | Redis 5 |
| Auth | JWT (python-jose, passlib/bcrypt) |
| File storage | Local filesystem (`backend/uploads/`) |
| Rate limiting | slowapi |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 18 + Vite 5 |
| UI library | Ant Design 5 + Pro Components |
| State | Redux Toolkit |
| Routing | React Router v6 |
| HTTP | Axios |
| i18n | react-i18next |
| Charts | Recharts, D3, d3-cloud |
| QR codes | qrcode.react |

---

## Project Structure

```
Swaya.me/
├── backend/
│   ├── main.py                        # FastAPI app entry point
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env                           # Environment config (not committed)
│   ├── uploads/                       # Image uploads (served at /api/uploads)
│   ├── broker/
│   │   └── api/                       # FastAPI routers (transport layer)
│   │       ├── routes.py              # Central API router
│   │       ├── auth.py
│   │       ├── quiz.py                # Quiz, question, session, answer endpoints
│   │       ├── quiz_admin.py          # Admin quiz management
│   │       ├── stats.py               # Admin stats + feedback
│   │       ├── user_management.py
│   │       ├── tenant_management.py
│   │       ├── organization_management.py
│   │       ├── tier_management.py
│   │       ├── language_tracking.py
│   │       └── uploads.py
│   ├── core/
│   │   ├── auth/                      # JWT auth, deps, schemas, service
│   │   ├── config/
│   │   │   ├── settings.py            # Pydantic settings (reads .env)
│   │   │   └── tier_service.py        # Tier quota enforcement
│   │   ├── security/                  # JWT creation, password hashing
│   │   ├── logging/
│   │   └── stats/                     # Stats service + scheduler
│   ├── features/
│   │   └── quiz/                      # Business logic (async preferred)
│   │       ├── quiz_service_async.py
│   │       ├── question_service_async.py
│   │       ├── session_service_async.py
│   │       ├── answer_service_async.py
│   │       ├── feedback_service_async.py
│   │       ├── platform_quiz_service_async.py
│   │       └── schemas.py
│   ├── persistence/
│   │   ├── database.py                # Sync SQLAlchemy engine
│   │   ├── database_async.py          # Async SQLAlchemy engine
│   │   ├── models/
│   │   │   ├── core.py                # Tenant, User, Event, TierConfig, LanguageEvent
│   │   │   ├── quiz.py                # Quiz, Question, QuizSession, Participant, Answer, QuizFeedback
│   │   │   └── stats.py
│   │   └── migrations/versions/       # Alembic migration files
│   ├── shared/
│   │   ├── exceptions/                # Domain exceptions (auth, quiz)
│   │   └── utils/
│   │       └── redis_client.py
│   └── scripts/
│       └── seed_data.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── dist/                          # Built output (served by Nginx)
    └── src/
        ├── App.jsx                    # Root router + ProLayout
        ├── main.jsx
        ├── services/api.js            # Axios API client (VITE_API_URL)
        ├── store/                     # Redux store + slices
        ├── components/                # Shared components
        ├── features/
        │   ├── home/Home.jsx          # Public landing page
        │   ├── auth/                  # Login + Register
        │   ├── dashboard/Dashboard.jsx
        │   ├── quiz/
        │   │   ├── QuizBuilder.jsx    # Create/edit quiz + questions
        │   │   └── QuizControl.jsx    # Live session control
        │   ├── audience/
        │   │   ├── AudienceJoin.jsx   # Join page (public)
        │   │   └── AudienceSession.jsx # Live participation (public)
        │   └── admin/
        │       ├── Statistics.jsx
        │       ├── UserManagement/
        │       ├── OrganizationManagement.jsx
        │       ├── FeedbackManagement.jsx
        │       ├── PlatformQuizzes.jsx
        │       └── TierManagement.jsx
        └── locales/                   # i18n JSON files (en, hi, ta, te, ka, bn, gu)
```

---

## Domain Model

### Core
- **Tenant** — isolated org/workspace, has tier (FREE/BASIC/PRO/ENTERPRISE)
- **User** — host user; roles: `super_admin`, `admin`, `user`, `viewer`
- **Event** — quiz event with optional join_code (set when session is live)
- **TierConfiguration** — per-tier limits (max_participants, max_questions, max_concurrent_events)

### Quiz
- **Quiz** — belongs to Event+Tenant; status: DRAFT → READY → ARCHIVED
- **Question** — MCQ (4 options, correct_answer_index) or WORD_CLOUD
- **QuizSession** — live instance; status: CREATED → ACTIVE → ENDED
- **Participant** — anonymous audience member with session_token
- **Answer** — participant response; MCQ has is_correct, word_cloud has text_answer
- **QuizFeedback** — post-session feedback from participants or users

---

## API Structure

All API routes are prefixed `/api/v1`.

| Prefix | Router | Notes |
|--------|--------|-------|
| `/api/v1/auth` | auth.py | Register, login, /me |
| `/api/v1/quizzes` | quiz.py | CRUD, publish, sessions, answers |
| `/api/v1/admin/stats` | stats.py | Admin only |
| `/api/v1/admin/users` | user_management.py | Admin only |
| `/api/v1/admin/organizations` | organization_management.py | Super admin |
| `/api/v1/admin/quizzes` | quiz_admin.py | Super admin |
| `/api/v1/admin/tier-configs` | tier_management.py | Super admin |
| `/api/v1/admin/feedback` | stats.py | Admin only |
| `/api/v1/uploads` | uploads.py | Image upload |
| `/api/uploads/*` | Static | Served files |

API docs: `https://www.swaya.me/api/docs`

---

## User Roles

| Role | Description |
|------|-------------|
| `super_admin` | Platform-level admin (tenant_id=1); manages all orgs/tiers |
| `admin` | Tenant-level admin; manages users within their org |
| `user` | Regular host; can create/run quizzes |
| `viewer` | Read-only access |

---

## Environment Variables (backend/.env)

Key variables (see `backend/core/config/settings.py` for full list):
```
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB
JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
HOST, PORT, DEBUG, ENVIRONMENT
ALLOWED_ORIGINS
```

Frontend env (`frontend/.env` or build-time):
```
VITE_API_URL=https://www.swaya.me/api/v1
```

---

## Development Notes

- **All new backend service code should use async** (`*_async.py` pattern); sync versions are legacy
- Backend uses **MySQL** (not SQLite/PostgreSQL)
- Redis is used for: session state, participant counts, rate limiting
- Image uploads stored at `backend/uploads/images/`; served at `/api/uploads/images/`
- Temp images at `backend/uploads/temp/`; cleaned up after 2 hours on startup
- Statistics snapshots run on a scheduler (APScheduler)
- Profanity filter: `better-profanity` library (word cloud answers)
- Alembic migration naming: `YYYYMMDD_HHMM_description.py`

---

## Testing

- **Manual/visual testing**: via `www.swaya.me` in browser
- **Selenium screen testing**: Docker container `seleniumarm` (ARM-based)
- **Unit tests**: pytest in `backend/` (`requirements-dev.txt`)
- **Load testing**: locust (included in requirements.txt)

---

## Docs

Project documentation in `Docs/`:
- `mvp-high-level-architecture.md` — architecture overview
- `quiz-feature-internals.md` — quiz domain logic
- `quiz-builder.md` — builder UX details
- `quiz-user-journey.md` — user journey flows
- `audience-join-quiz.md` — audience join flow
- `auth.md` — authentication design
- `business_scope.md` — business context
- `UI_Requirements.md` — UI specs
