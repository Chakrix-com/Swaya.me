# CLAUDE.md — Swaya.me Engineering Reference

Generated from code evidence only. Every rule cites a source file.

---

## 1. Critical Invariants

### Startup Sequence (must complete before any request is served)
Enforced by `backend/main.py:lifespan()` — all three must succeed before `yield`:
1. **Redis must connect** — `await redis_client.connect()`. Redis failure aborts startup entirely.
2. **APScheduler must start** — `start_scheduler()`. Failure aborts startup.
3. **Proctoring rules seeded** — `seed_platform_rules()`. Exceptions are caught/logged only — does NOT block startup.

### Auth Gate Sequence
Every protected route with `Depends(get_current_user)` (`core/auth/dependencies.py`) enforces ALL of:
1. `Authorization: Bearer {token}` header present
2. JWT signature valid + not expired (`core/security/jwt.py:decode_access_token`)
3. `User.id` from token exists in DB with `is_active=True`
4. `Tenant.id` from token exists in DB with `is_active=True`
5. `user.tenant_id == tenant.id`

Any failure → HTTP 401. Admin-only routes additionally require `role in (admin, super_admin)` → 403 otherwise.

### Email Verification
Users with `is_email_verified=False` cannot log in → HTTP 403.
Exception: `demo@swaya.me` bypasses this check.
Source: `core/auth/service_async.py:login_user()`

### Tenant Isolation
ALL quiz/session/participant reads in service layer must filter by `tenant_id == current_user.tenant_id`.
There is NO row-level security at the MySQL level — isolation is application-only.
Relevant guard: `broker/api/quiz.py:_assert_host_session_access()` (called before results, leaderboard, export).

### Quiz/Session State Machines
**Quiz**: `DRAFT → READY` (via `publish_quiz()`, requires ≥1 question) → `DRAFT` (via `unpublish_quiz()`).
Questions can only be added/edited/deleted when `quiz.status == DRAFT`.
Source: `features/quiz/question_service_async.py`

**Session**: `CREATED → ACTIVE` (first `advance_question()`) → `ENDED` (via `end_session()`).
`current_question_index` starts at `-1`. `QuestionStatus` transitions: `PENDING → OPEN → CLOSED`.
Source: `features/quiz/session_service_async.py`

### Proctoring Invariants
- Proctoring config is cached in Redis at `proctor:rules:{quiz_id}:{hash}` with 1h TTL. Changes to platform rules do NOT propagate to active sessions for up to 1 hour.
- Lock is permanent once set: `is_locked=True` in Redis can only be cleared by `unlock_session()` (admin endpoint).
- Exam content is blocked behind `ProctoringProvider` spinner until `ruleSet` is non-null (`frontend/src/features/proctoring/ProctoringProvider.jsx:93`).
- Fullscreen is a hard gate: `ProctoringGate.jsx:94` — `children` never rendered unless `document.fullscreenElement` is truthy.

### Redis Key Patterns That Cannot Be Renamed Without Breaking Live Sessions
| Key Pattern | Writer | Readers |
|---|---|---|
| `session_token:{token}` | `session_service_async.py:join_session()` | `broker/api/quiz.py:_require_participant_for_session()` |
| `proctor:session:{token}` | `proctoring_service_async.py:_set_redis_session()` | `proctoring_service_async.py:log_violation()`, `lock_session()` |
| `session:{id}:participants:count` | `tier_service.py:increment_participant_count()` | `tier_service.py:check_participant_limit()` |

---

## 2. Dangerous Areas — Do Not Touch Without Full Impact Analysis

### `broker/api/routes.py`
Central router registration. Changing any `prefix=` or `dependencies=` here affects ALL routes in that router.
Only safe operation: appending `api_router.include_router(...)`.

### JWT Payload Claims
Claims `sub`, `tenant_id`, `email`, `role`, `tier` are read in two places:
1. `core/auth/dependencies.py:get_current_user()`
2. `broker/policies/tenant_isolation.py:tenant_isolation_middleware()`

Renaming any claim invalidates all existing tokens (forces all users to re-login).

### MySQL ENUM Columns
`QuestionType`, `QuizType`, `UserRole`, `QuizStatus`, `SessionStatus` are ENUM columns.
Adding or renaming values requires an explicit Alembic migration with `ALTER TABLE ... MODIFY COLUMN`.
Alembic autogeneration does NOT handle MySQL enum changes correctly.

### `persistence/database.py` (Sync Engine)
Used ONLY by Alembic migrations (`env.py`). Do NOT import `get_db()` from this file in any new route or service.
All application code must use `from persistence.database_async import get_async_db`.

### Hardcoded Absolute Paths
Three locations in the codebase hardcode `/home/vinay/Swaya.me/`:
- `backend/main.py` (lines 33–34, 39–40, 111): uploads and temp directories
- `backend/broker/api/proctoring.py` (line 269): proctoring snapshot path

Any deployment to a different machine path requires these to be changed — they are not config-driven.

### `TenantContext` Module-Level Singleton
`broker/policies/tenant_isolation.py:21` — `tenant_context = TenantContext()` is a global object.
It is NOT request-scoped and is NOT safe under concurrent requests.
Do NOT read tenant_id from this object in business logic. Use `get_current_user()` dependency instead.

### SMTP Configuration
Email settings are read via bare `os.getenv()` in `core/auth/email_service.py`, NOT through the Pydantic `settings` object.
Failures are silently swallowed — emails are logged instead of sent. There is no startup validation.
Do NOT move SMTP vars to Pydantic settings without also updating all `os.getenv()` call sites.

---

## 3. Safe Zones for Modification

### Adding a New API Endpoint
Safe pattern — no cross-cutting impact:
1. Handler in `broker/api/{domain}.py`
2. Service function in `features/{domain}/{name}_service_async.py` (async only)
3. Pydantic schemas in `features/{domain}/schemas.py`
4. Register in `broker/api/routes.py` with `api_router.include_router(...)`
5. Add Alembic migration if new columns needed

### Adding/Editing Email HTML
HTML templates are Python string literals in `core/auth/email_service.py`.
Only placeholder in use is `{name}`. Changing HTML is safe; changing placeholder names requires updating matching `.format()` calls.

### Adding a New Locale
Safe — frontend-only change:
1. Create `frontend/src/locales/{code}.json`
2. Register in `frontend/src/i18n.js`
3. Add to `App.jsx:localeMap` and `LanguageSwitcher` component
Backend never returns localized strings.

### Adding a New Tier Check
1. Add check method to `core/config/tier_service.py`
2. Add key to `_get_default_limits()`
3. Call from the appropriate service
Note: Redis cache TTL is 5 minutes — limit changes propagate with up to 5 min lag.

### Adding a New Admin-Only Route
1. Create handler with `Depends(require_admin)` or `Depends(require_super_admin)`
2. Register via `api_router.include_router(router, prefix="/admin")`
Do NOT add `/admin` prefix inside the router file itself — it is applied at registration time.

### Modifying ORM Models — Adding a Column
1. Add field to `persistence/models/{domain}.py`
2. Create migration with naming pattern `YYYYMMDD_HHMM_description.py`
Adding a nullable column or a column with a default is non-breaking.

---

## 4. Mandatory Coding Patterns

### Async Services Only
All new backend service files must be named `*_service_async.py` and use `async def` throughout.
Legacy sync files (`quiz_service.py`, `session_service.py`, etc.) exist but must NOT be imported in new code.
Importing sync services into async FastAPI routes causes thread blocking.

### DB Session Dependency
```python
# CORRECT — always use this in route handlers and services
from persistence.database_async import get_async_db
async def handler(db: AsyncSession = Depends(get_async_db)): ...

# WRONG — sync session, Alembic-only
from persistence.database import get_db
```

### Tenant Scoping in Every Service Query
Every query that reads tenant-owned data must include a `tenant_id` filter.
Pattern from `features/quiz/quiz_service_async.py`:
```python
result = await db.execute(
    select(Quiz).where(Quiz.tenant_id == current_user.tenant_id, ...)
)
```
Omitting this filter is a data leak.

### Alembic Migration Naming
All migration files: `YYYYMMDD_HHMM_description.py`
Example: `20260418_1000_add_one_word_question_type.py`

### i18n for All User-Visible Strings
Every new UI label, error message, or button text must have a key in all 11 locale files:
`en, hi, ta, te, ka, bn, gu, es, fr, de, ru` under `frontend/src/locales/`.
Backend never localizes — all translation is frontend-only via `react-i18next`.

### New Proctoring Rules
Must be registered in `features/proctoring/rule_registry.py:PLATFORM_RULES`.
`rule_id` must be globally unique (DB UNIQUE constraint on `platform_proctoring_rules.rule_id`).
After adding: delete Redis keys matching `proctor:rules:*` to force immediate propagation.
Add corresponding i18n key `proctoring.warning.rules.{rule_id}` to all 11 locale files.

### Redis Key Hygiene
New Redis keys must NOT collide with existing patterns listed in Section 1.
Always set a TTL on new keys — no unbounded keys.
Key naming convention from codebase: `{domain}:{entity_id}:{property}`.

---

## 5. Known Gaps (NOT DERIVABLE FROM CODE — handle with care)

- **Real-time audience updates**: `python-socketio` is in requirements but has zero active routes. `AudienceSession.jsx:73-81` uses 2-second HTTP polling (`loadResults`) for session state updates.
- **Exam time enforcement**: Enforced server-side in `exam_service_async.py:197-202` — raises HTTP 410 if `elapsed > limit`.
- **Duplicate answer prevention**: No DB unique constraint on `(participant_id, question_id)`. Race condition possible under concurrent submissions. Do NOT rely on application-level SELECT-then-INSERT alone for correctness guarantees.
- **Proctoring bypass**: All face detection runs in the browser via MediaPipe (loaded from external CDN). Server receives only what the client reports. No server-side verification exists in reviewed code.
- **Ollama dependency**: AI features require `ollama` daemon running at `http://127.0.0.1:11434` with `qwen2.5:3b` model pre-pulled. Not health-checked at startup. Silent 503 if unavailable.
- **Tier counters after Redis flush**: `session:{id}:participants:count` in Redis is the source of truth for participant limits. If Redis is restarted, counters reset to 0 — tier limits are bypassable until the next join repopulates the counter.
- **Concurrent-Safe Session Restart**: `session_service_async.py:594-621` invalidates participants in DB and evicts tokens from Redis on session start.
