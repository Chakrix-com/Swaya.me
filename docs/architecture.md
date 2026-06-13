# Architecture

## System Overview

Swaya is a multi-tenant, real-time audience engagement platform. A single deployment hosts many independent organizations (tenants), each with isolated data, branding, and usage limits.

```
                        ┌─────────────────────────────────────────────┐
                        │                 Browser Clients              │
                        │                                              │
                        │  Host (admin)      Audience (anonymous)      │
                        └────────┬──────────────────┬─────────────────┘
                                 │  HTTPS           │  HTTPS
                        ┌────────▼──────────────────▼─────────────────┐
                        │               Nginx (reverse proxy)          │
                        │  /            → frontend/dist (static)       │
                        │  /api/*       → FastAPI :8000                │
                        └────────────────────────┬────────────────────┘
                                                 │
                        ┌────────────────────────▼────────────────────┐
                        │              FastAPI (Python 3.10)           │
                        │                                              │
                        │  broker/api/   ← 20 API routers             │
                        │  features/     ← async service layer         │
                        │  core/         ← auth, security, AI, config  │
                        │  persistence/  ← SQLAlchemy models + DAL     │
                        └──────────┬──────────────────┬───────────────┘
                                   │                  │
                    ┌──────────────▼──┐    ┌──────────▼──────────┐
                    │   MySQL 8        │    │      Redis 7         │
                    │                  │    │                      │
                    │  All persistent  │    │  JWT blocklist       │
                    │  application     │    │  Session pub-sub     │
                    │  data            │    │  Rate-limit state    │
                    │  (tenant-scoped) │    │  Tier cache (5 min)  │
                    │                  │    │  OTP storage (10 min)│
                    │                  │    │  OAuth CSRF state    │
                    └──────────────────┘    └─────────────────────┘
```

---

## Request Lifecycle

### Authenticated Request

1. Browser sends request with `access_token` HttpOnly cookie.
2. Nginx forwards to FastAPI.
3. `get_current_user` dependency decodes JWT, checks Redis blocklist, returns `CurrentUser`.
4. Tenant middleware validates `tenant_id` from token.
5. Service function queries MySQL with tenant filter, returns response.

### Public Audience Request (exam, poll)

1. Browser sends `session_token` in request body (opaque token issued at exam start).
2. FastAPI resolves participant by token, scopes all DB queries to that exam.
3. No JWT, no cookies — participants are never system users.

---

## Real-time Architecture (SSE)

Live quiz sessions use **Server-Sent Events**, not WebSockets. Each quiz session has a Redis pub-sub channel.

```
Host triggers event
        │
        ▼
FastAPI publishes to Redis channel  →  Redis broadcasts
                                             │
                                    ┌────────▼────────┐
                                    │  SSE endpoint   │  ← one open connection per audience member
                                    │  /api/v1/events │
                                    │  /session/{id}  │
                                    └────────┬────────┘
                                             │ text/event-stream
                                             ▼
                                      Audience browser
                                      (@microsoft/fetch-event-source
                                       with polling fallback)
```

Why SSE instead of WebSockets:
- Audience connections are unidirectional (server → client only).
- SSE works through all HTTP/1.1 proxies without upgrade headers.
- Polling fallback handles environments that kill long connections.
- See [tech-choices.md](tech-choices.md) for the full rationale.

---

## Service Layer

Business logic lives in `backend/features/*/`. The naming convention is:

| File | Status |
|---|---|
| `*_service_async.py` | **Active** — async SQLAlchemy, all new code goes here |
| `*_service.py` | Legacy sync — do not add new functions |

Service functions receive an `AsyncSession` from FastAPI's `Depends(get_async_db)` and own all DB logic. API routers (`broker/api/`) are thin: validate input, call service, map exceptions to HTTP errors.

---

## Directory Map

```
Swaya.me/
├── backend/
│   ├── main.py                        # FastAPI app factory + middleware registration
│   ├── broker/
│   │   ├── api/routes.py              # Central router (20 sub-routers registered here)
│   │   ├── api/*.py                   # One file per domain (auth, quiz, exam, ai, …)
│   │   └── policies/tenant_isolation.py  # Middleware: extract tenant_id from JWT
│   ├── core/
│   │   ├── config/settings.py         # All config — Pydantic BaseSettings, env-var driven
│   │   ├── auth/                      # JWT encode/decode, OAuth, dependencies
│   │   ├── security/jwt.py            # Token creation, revocation (Redis blocklist)
│   │   ├── ai/gemini_service.py       # Gemini 2.0 Flash — question gen + result analysis
│   │   └── storage/image_service.py   # Upload handling + S3-compatible path logic
│   ├── features/
│   │   ├── quiz/                      # Quiz, session, exam, poll, import, word cloud
│   │   ├── app_feedback/              # In-app feedback collection
│   │   └── platform_metrics/          # PlatformEvent beacon storage
│   ├── persistence/
│   │   ├── models/core.py             # Tenant, User, Event, TierConfig
│   │   ├── models/quiz.py             # Quiz, Question, Session, Participant, Answer, Feedback
│   │   └── migrations/                # Alembic — naming: YYYYMMDD_HHMM_description.py
│   └── shared/
│       └── utils/                     # Redis client, rate limiter, HTML sanitizer, email
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Root routes + ProLayout (public vs authenticated shell)
│   │   ├── features/                  # Feature components grouped by domain
│   │   ├── services/api.js            # All Axios API calls (single source of truth)
│   │   ├── store/                     # Redux Toolkit slices
│   │   └── locales/                   # 11× translation.json files
│   └── vite.config.js
└── docs/                              # This documentation
```

---

## Data Model (Key Entities)

```
Tenant ──< User
Tenant ──< Quiz ──< Question ──< QuestionOption
                Quiz ──< QuizSession ──< Participant ──< Answer
                                    QuizSession ──< ProctoringSnapshot
TierConfig (per tenant)
PlatformEvent (analytics beacon)
```

Every quiz, question, session, and participant record carries `tenant_id`. No cross-tenant query is possible without explicitly bypassing the tenant filter — service functions never do this.

---

## Auth Flow

```
Login (email/password or Google OAuth)
        │
        ▼
FastAPI issues JWT (HS256, 8h expiry, unique jti claim)
        │
        ▼
Set as HttpOnly Secure SameSite=Lax cookie  ←── primary channel
(Bearer header also accepted for API clients)
        │
        ▼
On logout: jti added to Redis blocklist (TTL = remaining JWT lifetime)
Every authenticated request: blocklist check before user resolution
```

See [security.md](security.md) for full detail.
