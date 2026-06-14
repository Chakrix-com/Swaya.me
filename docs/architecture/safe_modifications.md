# Safe Modifications Guide

---

## Adding a New API Endpoint

### Safe Pattern
1. Create handler in existing or new `broker/api/{domain}.py` file
2. Define Pydantic request/response schemas inline or in `features/{domain}/schemas.py`
3. Create service function in `features/{domain}/{name}_service_async.py` — async only
4. Import and register router in `broker/api/routes.py`
5. Add migration if new DB columns needed

### Files to Modify
| What | File |
|---|---|
| Route handler | `broker/api/{domain}.py` |
| Business logic | `features/{domain}/{name}_service_async.py` |
| Schemas | `features/{domain}/schemas.py` |
| Router registration | `broker/api/routes.py` |
| DB model (if new table/column) | `persistence/models/{domain}.py` + new Alembic migration |
| Frontend API call | `frontend/src/services/api.js` |

### What NOT to Change
- **Do NOT** modify `broker/api/routes.py` in any way other than adding `api_router.include_router()` — changing prefix or auth defaults here affects all routes in that router
- **Do NOT** add new sync service files (`*_service.py`) — only async (`*_service_async.py`)
- **Do NOT** use `from persistence.database import get_db` in new code — always use `from persistence.database_async import get_async_db`

---

## Adding a New Question Type

### Files to Modify
1. `persistence/models/quiz.py` — add value to `QuestionType` enum
2. New Alembic migration in `persistence/migrations/versions/` to ALTER the enum (MySQL requires explicit ALTER)
3. `features/quiz/question_service_async.py` — handle new type in `add_question()` / `update_question()`
4. `features/quiz/answer_service_async.py` — handle scoring/aggregation for new type
5. `features/quiz/export_service.py` — add export rendering if needed
6. Frontend: `features/quiz/QuizBuilder` and `features/audience/AudienceSession`
7. All 11 i18n locale files in `frontend/src/locales/` for UI labels

### Caution
- MySQL enum changes require a migration; the enum column does NOT auto-update from Python
- Answer submission validation (`QuestionNotOpenError`, duplicate check) applies to all types — review `answer_service_async.py` logic

---

## Adding a New Tier Limit

### Files to Modify
1. `core/config/tier_service.py` — add new check method (e.g. `check_export_limit()`)
2. `core/config/tier_service.py:_get_default_limits()` — add new key
3. The specific service that enforces the limit (e.g. `features/quiz/quiz_service_async.py`)
4. No migration needed if limit enforced in application only; migration needed if storing limit in `tier_configurations.features` JSON

### Caution
- `TierConfiguration.features` is a JSON TEXT column — NOT a validated schema
- `tier_config:{tier}` is cached in Redis for 5 minutes — changes to `tier_configurations` table need 5 min to propagate

---

## Adding a New Proctoring Rule

### Files to Modify
1. `features/proctoring/rule_registry.py` — add entry to `PLATFORM_RULES` list (seeded at startup)
2. `features/proctoring/context_resolver.py` — no change needed if rule follows existing pattern
3. Frontend: `features/proctoring/hooks/useProctoringModule.js` — add event listener for the rule
4. Frontend: `features/proctoring/ProctoringGate.jsx:RULE_KEYS` array — add rule_id to display in warning screen
5. All 11 i18n locale files — add `proctoring.warning.rules.{rule_id}` key

### Caution
- Rules are seeded at startup via `seed_platform_rules()` in `main.py:lifespan()`
- Existing cached rule sets in Redis (`proctor:rules:*`) will NOT pick up new rules for up to 1 hour
- To force immediate refresh: manually delete Redis keys matching `proctor:rules:*`
- `rule_id` must be globally unique (UNIQUE constraint on `platform_proctoring_rules.rule_id`)

---

## Adding a New Locale (Language)

### Files to Modify
1. Create `frontend/src/locales/{code}.json` — copy `en.json` as base, translate all keys
2. `frontend/src/i18n.js` (or equivalent init file) — add import and resource entry
3. `frontend/src/App.jsx:localeMap` — add entry mapping language code to Ant Design locale (or `enUS` fallback)
4. `frontend/src/components/LanguageSwitcher` — add option to dropdown

### What NOT to Change
- Do NOT add backend locale support — all i18n is frontend-only; backend never returns localized strings in current code

---

## Adding a New Admin Route

### Files to Modify
1. Create handler in `broker/api/{name}.py` with `router = APIRouter(tags=[...])`
2. Use `Depends(require_admin)` or `Depends(require_super_admin)` as appropriate
3. `broker/api/routes.py` — `api_router.include_router(router, prefix="/admin", tags=["admin"])`

### Caution
- Prefix `/admin` is applied at `routes.py` include time — do NOT add `/admin` prefix to the router's own prefix in the file
- `require_admin` allows both `admin` AND `super_admin` roles; `require_super_admin` allows only `super_admin`

---

## Modifying the JWT Payload

### Risk: HIGH
- JWT payload claims (`sub`, `email`, `tenant_id`, `tier`, `role`) are read in TWO places:
  1. `core/auth/dependencies.py:get_current_user()` — reads `sub` and `tenant_id`
  2. `broker/policies/tenant_isolation.py:tenant_isolation_middleware()` — reads `tenant_id`
- **All existing tokens become invalid** if you rename claims — users must re-login
- **Do NOT change** the `sub` claim name — it is the JWT standard for subject (user_id)

### Safe Change
- Adding new claims to the payload is safe — existing validators only read known claims
- Removing claims: check both consumers above before removing

---

## Modifying ORM Models

### Adding a Column
1. Add column to `persistence/models/{domain}.py`
2. Create Alembic migration: `alembic revision -m "YYYYMMDD_HHMM_description"` in `backend/`
3. For ENUM column changes in MySQL: write explicit `ALTER TABLE ... MODIFY COLUMN` in migration — Alembic auto-generation may not handle MySQL enum changes correctly

### Renaming/Removing a Column
- **Risk: HIGH** — breaks all queries that reference the column
- Must update: ORM model, all service files that query/write the column, migration
- Alembic `op.drop_column()` is irreversible — ensure no data is needed before dropping

### Adding a Relationship
- Safe if it's `lazy="select"` (default) — does NOT change DB schema
- If adding `cascade="all, delete-orphan"`: verify this is intentional; cascades are permanent

---

## Modifying Redis Key Patterns

### Risk: HIGH
- Redis keys are used as caches and fast-path lookups in production
- `session_token:{token}` is used in `_require_participant_for_session()` — wrong format breaks answer submission for ALL active sessions
- `proctor:session:{token}` is used in every proctoring violation call — wrong format disables proctoring enforcement

### Safe Pattern
- Add new key patterns for new features; do NOT rename existing patterns
- If a key pattern must change: update both writer and reader atomically (single deploy)

### Key Patterns That Cannot Be Changed Without Breaking Live Sessions
| Key | Writer | Readers |
|---|---|---|
| `session_token:{token}` | `session_service_async.py:join_session()` | `broker/api/quiz.py:_require_participant_for_session()` |
| `proctor:session:{token}` | `proctoring_service_async.py:_set_redis_session()` | `proctoring_service_async.py:log_violation()`, `_check_escalation()`, `lock_session()` |
| `session:{id}:participants:count` | `tier_service.py:increment_participant_count()` | `tier_service.py:check_participant_limit()` |

---

## Modifying Email Templates

### Safe
- HTML content of emails is in `core/auth/email_service.py` as Python string templates
- Only `{name}` placeholder is used in `WELCOME_EMAIL_HTML`
- Changing HTML is safe; changing the placeholder variable name requires matching the `format()` call

### What NOT to Change
- `SMTP_*` environment variable names — read via `os.getenv()` (not Pydantic); no validation
- Email sending is async but errors are silently caught — do NOT make email sending blocking (it will hold up registration/login)

---

## Modifying Tier Default Limits

### Files to Change
1. `core/config/tier_service.py:_get_default_limits()` — these are fallback defaults when no DB row exists
2. Optionally: `seed_tier_configurations()` in same file — for initial seeding

### Caution
- If `tier_configurations` table has rows, the DB values override defaults (`_get_default_limits()` is only called when `scalar_one_or_none()` returns None)
- Redis cache TTL is 5 minutes — changes take up to 5 min to propagate
- The actual enforced limits come from DB first → Redis cache → code defaults (in that precedence)

---

## Adding a New Quiz Type

### Risk: HIGH (cascading changes required)
1. `persistence/models/quiz.py:QuizType` enum — add new value
2. Alembic migration to ALTER MySQL enum column
3. `features/quiz/quiz_service_async.py` — handling in `publish_quiz()` and any type-specific publish methods
4. `features/quiz/session_service_async.py:_write_audience_state_cache()` — `is_poll = session.quiz.quiz_type == QuizType.POLL` pattern may need extension
5. `features/quiz/export_service.py` — new type needs export handling
6. Frontend: QuizBuilder type selector, audience session rendering, results display
7. Proctoring `applies_to.quiz_types` — rule registry may need updating

### Coupling Points to Understand First
- `session_service_async.py` has conditional logic on `quiz_type` (poll vs non-poll for scoring/leaderboard)
- `answer_service_async.py` has type-specific answer handling
- `exam_service_async.py` is specific to `QuizType.EXAM`
- `offline_poll_service_async.py` is specific to `QuizType.OFFLINE_POLL`
