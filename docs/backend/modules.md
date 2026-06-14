# Backend Modules

## Package Structure

```
backend/
├── main.py                     — FastAPI app creation, lifespan, middleware
├── broker/
│   ├── api/                    — All route handlers (one file per domain)
│   └── policies/               — HTTP middleware
├── core/
│   ├── ai/                     — Ollama LLM service
│   ├── auth/                   — Auth service, JWT dependencies, email
│   ├── config/                 — Settings, tier enforcement
│   ├── language_tracking/      — Language event service
│   ├── logging/                — Logging config
│   ├── organization/           — Organization management service
│   ├── security/               — Password hashing, JWT operations
│   ├── stats/                  — Snapshot scheduler, snapshot service
│   ├── storage/                — Image upload/temp cleanup
│   └── user_management/        — User CRUD service
├── features/
│   ├── proctoring/             — Proctoring session, violation, rule services
│   └── quiz/                   — All quiz business logic
├── persistence/
│   ├── database.py             — Sync engine (Alembic only)
│   ├── database_async.py       — Async engine + session factory
│   ├── migrations/             — Alembic version files
│   └── models/                 — SQLAlchemy ORM models
└── shared/
    ├── exceptions/             — Domain exception classes
    └── utils/                  — Redis client, misc utilities
```

---

## Module Details

### `main.py`
- **Responsibility**: Application factory (`create_application()`), lifespan context manager
- **Key functions**: `create_application()`, `lifespan(app)`
- **Dependencies**: `core/config/settings.py`, `broker/api/routes.py`, `shared/utils/redis_client.py`, `broker/policies/tenant_isolation.py`, `core/stats/scheduler.py`
- **Side effects on startup**: Redis connect, uploads dir create, temp cleanup, scheduler start, proctoring rule seed

---

### `broker/api/` — Route Handlers

Each file defines a single `router` (APIRouter) imported into `broker/api/routes.py`.

| File | Prefix | Auth Requirement |
|---|---|---|
| `auth.py` | `/auth` | Mixed (most endpoints public or auth-optional) |
| `quiz.py` | `/quizzes` | Most require auth; join/submit are anonymous |
| `exam.py` | none | Public for `/e/{slug}`; auth for host management |
| `offline_poll.py` | `/offline-poll` | Public for participation; auth for results |
| `proctoring.py` | `/proctoring` | Mixed; most participant endpoints use session token header |
| `ai.py` | `/ai` | `require_admin` for generate; any auth for rewrite |
| `stats.py` | `/admin` (via routes.py) | Auth + admin role |
| `stats_history.py` | none (added via routes.py) | Auth |
| `uploads.py` | `/uploads` | Auth |
| `user_management.py` | `/users` | Auth |
| `tenant_management.py` | `/tenants` | Auth + super_admin |
| `organization_management.py` | `/admin` (via routes.py) | Auth + admin |
| `language_tracking.py` | mixed | Mixed |
| `quiz_admin.py` | `/admin` (via routes.py) | Auth + super_admin |
| `tier_management.py` | `/admin` (via routes.py) | Auth + super_admin |
| `og.py` | `/og` | Public |
| `offline_poll.py` | `/offline-poll` | Mixed |
| `app_feedback.py` | `/feedback` | Public for submit; auth for admin list |

---

### `broker/policies/tenant_isolation.py`
- **Responsibility**: HTTP middleware that extracts `tenant_id` from Bearer token into `TenantContext`
- **Key function**: `tenant_isolation_middleware(request, call_next)`
- **Note**: Context stored in module-level singleton `tenant_context`; not thread-safe for multi-worker but all actual tenant scoping happens in `get_current_user()` dependency via DB lookup

---

### `core/auth/`

#### `service_async.py`
- **Responsibility**: Registration, login, OAuth, password reset business logic
- **Key functions**: `register_user()`, `login_user()`, `oauth_login_or_register()`, `request_password_reset()`, `execute_password_reset()`
- **DB operations**: SELECT/INSERT User, Tenant; INSERT Event/Quiz/Questions at registration
- **Dependencies**: `core/security/password.py`, `core/security/jwt.py`, `core/auth/email_service.py`

#### `dependencies.py`
- **Responsibility**: FastAPI dependency injection for auth
- **Key classes**: `CurrentUser` — wraps `User` + `Tenant` objects
- **Key functions**: `get_current_user()`, `get_optional_user()`, `require_admin()`, `require_super_admin()`
- **Auth flow**: Extract Bearer token → `decode_access_token()` → SELECT User + Tenant → return `CurrentUser`

#### `email_service.py`
- **Responsibility**: Transactional email via fastapi-mail (SMTP)
- **Key functions**: `send_verification_email()`, `send_password_reset_email()`, `send_welcome_email()`, `send_email()`
- **Configuration**: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_PORT`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`
- **Fallback**: If SMTP unconfigured, emails are logged only

---

### `core/security/`

#### `jwt.py`
- **Responsibility**: JWT encode/decode
- **Key functions**: `create_access_token(data, expires_delta?)`, `decode_access_token(token)`
- **Algorithm**: HS256 (from `settings.jwt.algorithm`)
- **Expiry**: Default 24h (`settings.jwt.expiration_hours`)
- **Payload fields encoded**: `sub` (user_id), `email`, `tenant_id`, `tier`, `role`, `exp`, `iat`
- **Exceptions raised**: `ExpiredTokenError`, `InvalidTokenError` (from `shared/exceptions/auth.py`)

#### `password.py`
- **Responsibility**: bcrypt hashing via passlib
- **Key functions**: `hash_password(plain)`, `verify_password(plain, hashed)` (NOT DERIVABLE from reviewed code — only imported; implementation assumed in `core/security/password.py`)

---

### `core/config/settings.py`
- **Responsibility**: All configuration via Pydantic BaseSettings from `.env`
- **Classes**: `DatabaseSettings`, `RedisSettings`, `JWTSettings`, `AppSettings`, `GoogleSettings`, `Settings`
- **Global instance**: `settings = Settings()`
- **Key properties**: `DatabaseSettings.url` (sync), `DatabaseSettings.async_url` (async), `RedisSettings.url`

---

### `core/config/tier_service.py`
- **Class**: `TierService(redis: RedisClient)`
- **Responsibility**: Enforce per-tier limits; cache config in Redis
- **Key methods**: `get_tier_config(db, tier)`, `check_participant_limit()`, `check_question_limit()`, `check_concurrent_events_limit()`, `increment_participant_count()`, `decrement_participant_count()`
- **Cache key pattern**: `tier_config:{tier_value}` — 5-minute TTL
- **Participant count key**: `session:{session_id}:participants:count`

---

### `core/ai/ollama_service.py`
- **Responsibility**: Async HTTP client for local Ollama daemon
- **Key functions**: `generate_questions()`, `generate_distractors()`, `generate_poll_prompt()`, `rewrite_text()`, `list_available_models()`
- **Internal**: `_generate(prompt, model, ...)` — POST to `http://127.0.0.1:11434/api/generate`
- **Models**: DEFAULT `qwen2.5:3b`, FALLBACK `llama3.2:1b`
- **Error**: `OllamaError` raised on connection failure or HTTP error

---

### `core/stats/scheduler.py`
- **Responsibility**: Background APScheduler for stats snapshots
- **Key functions**: `start_scheduler()`, `stop_scheduler()`, `capture_hourly_snapshots()`, `capture_daily_snapshots()`
- **Jobs**: hourly (every `:00`), daily (midnight UTC)
- **Dependencies**: `core/stats/snapshot_service_async.py`, `AsyncSessionLocal`

---

### `features/quiz/`

#### `quiz_service_async.py` — `QuizBuilderServiceAsync`
- **Responsibility**: Quiz CRUD, template management, folder management, offline poll publish
- **Key methods**: `create_quiz()`, `get_quiz()`, `list_quizzes()`, `update_quiz()`, `delete_quiz()`, `publish_quiz()`, `publish_offline_poll()`, `duplicate_quiz()`, `create_quiz_from_template()`, `list_available_templates()`, `set_template_status()`, folder CRUD methods
- **Dependencies**: `TierService` (via constructor)

#### `question_service_async.py` — `QuestionServiceAsync`
- **Responsibility**: Question CRUD within quizzes
- **Key methods**: `add_question()`, `update_question()`, `delete_question()`, `reorder_questions()`
- **Guards**: Only allows modification when quiz status is DRAFT; checks tier question limit; applies content filter

#### `session_service_async.py` — `SessionServiceAsync`
- **Responsibility**: Live session lifecycle management
- **Key methods**: `start_session()`, `join_session()`, `leave_session()`, `advance_question()`, `back_question()`, `end_session()`, `toggle_leaderboard()`, `get_whiteboard_state()`, `update_whiteboard_state()`, `reconcile_timed_question_state()`
- **Redis usage**: Audience state cache, participant token cache, participant count counters
- **Dependencies**: `RedisClient`, `TierService`

#### `answer_service_async.py` — `AnswerServiceAsync`
- **Responsibility**: Answer submission, results aggregation, leaderboard
- **Key methods**: `submit_answer()`, `submit_word_cloud_answer()`, `get_session_results()`, `get_leaderboard()`, `get_word_cloud_results()`
- **Redis**: Answer distribution counters

#### `feedback_service_async.py` — `FeedbackServiceAsync`
- **Responsibility**: Quiz feedback submission for participants and authenticated users

#### `exam_service_async.py`
- **Responsibility**: Exam lifecycle — info, start, save answer, submit, score, results
- **Key functions**: `get_exam_info()`, `start_exam()`, `save_answer()`, `submit_exam()`, `get_my_result()`, `get_exam_results()`, `publish_exam()`, `unpublish_exam()`

#### `offline_poll_service_async.py`
- **Key functions**: `get_poll_info()`, `join_or_resume()`, `save_answer()`, `complete_poll()`, `get_results()`

#### `export_service.py` — `ExportService`
- **Responsibility**: Export session results to PDF/DOCX/PPTX/XLSX
- **Key method**: `generate(session_id, format, db, tenant_id, answer_service)` → returns `(file_bytes, media_type, filename)`
- **Dependencies**: reportlab (PDF), python-docx (DOCX), python-pptx (PPTX), openpyxl (XLSX), wordcloud+Pillow

#### `import_service.py` — `ExcelImportService`
- **Responsibility**: Excel import for bulk question creation
- **Key methods**: `parse_excel()`, `validate_import()`, `create_from_import()`, `generate_excel_from_draft()`
- **Dependencies**: openpyxl

#### `platform_quiz_service_async.py`
- **Responsibility**: Super-admin view of all quizzes across tenants

#### Legacy sync files (DO NOT USE for new code)
- `quiz_service.py`, `question_service.py`, `session_service.py`, `answer_service.py`

---

### `features/proctoring/`

#### `proctoring_service_async.py`
- **Responsibility**: Session initialization, violation logging, lock/unlock, biometric scoring
- **Key functions**: `init_session()`, `update_webcam_granted()`, `get_config()`, `log_violation()`, `lock_session()`, `unlock_session()`, `check_integrity()`, `get_violation_report()`, `ingest_biometric_sample()`
- **Redis key**: `proctor:session:{token}` — 24h TTL

#### `context_resolver.py` — `ProctoringContextResolver`
- **Responsibility**: Merge platform rules + tenant overrides + quiz policy into `ResolvedRuleSet`
- **Key method**: `resolve(context, quiz_proctoring_policy, db, redis)`
- **Cache key**: `proctor:rules:{quiz_id}:{context_hash}` — 1h TTL

#### `rule_registry.py`
- **Function**: `seed_platform_rules(db)` — populates `platform_proctoring_rules` table on startup

#### `violation_service.py`
- **Responsibility**: Violation count and escalation logic

#### `integrity_scorer.py` — `IntegrityScorer`
- **Method**: `score(sample, current_score)` — adjusts integrity score based on biometric sample

#### `honeypot_service.py` — `honeypot_service` singleton
- **Responsibility**: Generate and validate honeypot traps for exam sessions
- **Methods**: `generate(quiz_id, participant_id, type, redis)`, `validate_hit(session_token, trap, db, redis)`

#### `watermark_service.py`
- **Responsibility**: Participant-specific watermark generation for displayed content

---

### `persistence/`

#### `database.py`
- **Purpose**: Sync engine and Base — used only by Alembic migrations
- **Exports**: `Base`, `get_db()` (sync session dependency)

#### `database_async.py`
- **Purpose**: Async engine and session factory for all production code
- **Exports**: `async_engine`, `AsyncSessionLocal`, `get_async_db()` (FastAPI dependency)
- **Config**: `pool_size`, `max_overflow`, `pool_recycle` from settings; `pool_pre_ping=True`

#### `migrations/`
- 20+ Alembic version files named `YYYYMMDD_HHMM_description.py`
- Earliest: `20260208_0113_initial_schema.py`
- Recent additions: exam type, offline poll, quiz folders, proctoring tables

---

### `shared/`

#### `utils/redis_client.py` — `RedisClient`
- **Responsibility**: Redis connection wrapper with connection pooling
- **Methods**: `connect()`, `disconnect()`, `get()`, `set()`, `delete()`, `exists()`, `increment()`, `expire()`, `get_json()`, `set_json()`, `mget()`, `incrby()`
- **Global**: `redis_client = RedisClient()` singleton; `get_redis()` FastAPI dependency

#### `exceptions/auth.py`
- `InvalidCredentialsError`, `UserNotFoundError`, `DuplicateUserError`, `TenantNotFoundError`, `EmailNotVerifiedError`, `InvalidTokenError`, `ExpiredTokenError`

#### `exceptions/quiz.py`
- `QuizNotFoundError`, `QuestionNotFoundError`, `SessionNotFoundError`, `ParticipantNotFoundError`, `QuizValidationError`, `InvalidQuizStatusError`, `InvalidSessionStatusError`, `DuplicateAnswerError`, `QuestionNotOpenError`, `TierLimitExceededError`, `ContentFilterError`
