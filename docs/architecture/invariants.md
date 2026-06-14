# Architecture Invariants

Provable rules from source code only. Each rule cites exact file + function/model.

---

## Data Constraints (DB-Level)

### Unique Constraints
| Table | Unique Columns | Source |
|---|---|---|
| `tenants` | `slug` | `persistence/models/core.py:Tenant.slug` |
| `users` | `email` | `persistence/models/core.py:User.email` |
| `users` | `reset_password_token` | `persistence/models/core.py:User.reset_password_token` |
| `events` | `join_code` | `persistence/models/core.py:Event.join_code` |
| `quizzes` | `poll_slug` | `persistence/models/quiz.py:Quiz.poll_slug` |
| `quizzes` | `exam_slug` | `persistence/models/quiz.py:Quiz.exam_slug` |
| `participants` | `session_token` | `persistence/models/quiz.py:Participant.session_token` |
| `tier_configurations` | `tier` | `persistence/models/core.py:TierConfiguration.tier` |
| `platform_proctoring_rules` | `rule_id` | `persistence/models/proctoring.py:PlatformProctoringRule.rule_id` |
| `quiz_folders` | `(tenant_id, parent_id, name)` | `persistence/models/quiz.py:QuizFolder.__table_args__` |

### NOT NULL Constraints (Selected Critical Fields)
| Table | Field | Source |
|---|---|---|
| `tenants` | `name`, `slug`, `tier`, `is_active` | `persistence/models/core.py` |
| `users` | `email`, `is_active`, `role`, `is_email_verified`, `login_count` | `persistence/models/core.py` |
| `users` | `tenant_id` (FK, NOT NULL) | `persistence/models/core.py` |
| `quizzes` | `tenant_id`, `event_id`, `title`, `quiz_type`, `status` | `persistence/models/quiz.py` |
| `quiz_sessions` | `tenant_id`, `quiz_id`, `status`, `current_question_index` | `persistence/models/quiz.py` |
| `participants` | `session_id`, `session_token`, `is_active` | `persistence/models/quiz.py` |
| `answers` | `session_id`, `participant_id`, `question_id` | `persistence/models/quiz.py` |
| `proctoring_sessions` | `participant_id`, `quiz_id`, `tenant_id`, `active_rule_set` | `persistence/models/proctoring.py` |

### Foreign Key Constraints (Enforced by DB)
| Table.Column | References | On Delete |
|---|---|---|
| `users.tenant_id` | `tenants.id` | (default — restrict) |
| `users.managed_by_admin_id` | `users.id` | SET NULL |
| `events.tenant_id` | `tenants.id` | (default) |
| `events.creator_id` | `users.id` | (default) |
| `quizzes.event_id` | `events.id` | (default) |
| `quizzes.folder_id` | `quiz_folders.id` | SET NULL |
| `quiz_folders.parent_id` | `quiz_folders.id` | CASCADE |
| `questions.quiz_id` | `quizzes.id` | (default; ORM cascade via relationship) |
| `quiz_sessions.quiz_id` | `quizzes.id` | (default) |
| `participants.session_id` | `quiz_sessions.id` | (default) |
| `answers.session_id` | `quiz_sessions.id` | (default) |
| `answers.participant_id` | `participants.id` | (default) |
| `answers.question_id` | `questions.id` | (default) |
| `session_question_timings.session_id` | `quiz_sessions.id` | (default) |
| `user_activities.user_id` | `users.id` | CASCADE |
| `user_activities.tenant_id` | `tenants.id` | CASCADE |
| `stats_snapshots.tenant_id` | `tenants.id` | CASCADE |

**Note**: `proctoring_sessions`, `proctoring_events`, `tenant_proctoring_policies`, and `app_feedback` tables have NO FK constraints — plain integer columns.

---

## Required Call Sequences

### Startup Sequence (must complete before serving traffic)

Enforced by `asynccontextmanager` in `backend/main.py:lifespan()`:

1. **Redis must connect before serving**: `await redis_client.connect()` called in `lifespan()` before `yield`. If Redis connection fails, lifespan raises and FastAPI does not start.
2. **Proctoring rules seeded before serving**: `seed_platform_rules(seed_db)` called before `yield`. Exceptions are caught and logged — does NOT block startup.
3. **Scheduler started before serving**: `start_scheduler()` called before `yield` — exceptions would propagate and block startup.

### Auth Gate for Protected Endpoints

Any route handler that declares `current_user: CurrentUser = Depends(get_current_user)` requires:
1. Valid `Authorization: Bearer {token}` header present
2. `decode_access_token(token)` succeeds (valid signature, not expired)
3. `User.id` from token payload exists in DB and `is_active=True`
4. `Tenant.id` from token payload exists in DB and `is_active=True`
5. `user.tenant_id == tenant.id`

If ANY of these fail → HTTP 401. Source: `core/auth/dependencies.py:get_current_user()`

### Admin-Only Endpoints

Routes using `Depends(require_admin)` additionally require:
- `current_user.user.role in (UserRole.admin, UserRole.super_admin)`
- Otherwise → HTTP 403. Source: `core/auth/dependencies.py:require_admin()`

Routes using `Depends(require_super_admin)` require:
- `current_user.user.role == UserRole.super_admin`
- Otherwise → HTTP 403. Source: `core/auth/dependencies.py:require_super_admin()`

---

## Tenant Isolation Rules

### Provable from Code

1. **Quiz reads are tenant-scoped**: All quiz fetches in `QuizBuilderServiceAsync` filter by `quiz.tenant_id == current_user.tenant_id`. Source: `features/quiz/quiz_service_async.py`

2. **Session access requires tenant match**: `_assert_host_session_access()` in `broker/api/quiz.py` filters by `QuizSession.tenant_id == current_user.tenant_id`. This guard is called before results, leaderboard, and export endpoints.

3. **Proctoring report is tenant-scoped**: `broker/api/proctoring.py:get_report()` checks `quiz.tenant_id != current_user.tenant_id` → 403.

4. **Tier enforcement is tenant-scoped**: `TierService.check_concurrent_events_limit()` filters by `QuizSession.tenant_id == tenant_id`. Source: `core/config/tier_service.py`

5. **Template visibility**: `list_available_templates()` returns templates where `template_scope == "global"` OR `tenant_id == current_user.tenant_id`. Source: `features/quiz/quiz_service_async.py` (exact query NOT DERIVABLE from reviewed portion).

### Tenant Isolation NOT Enforced At DB Level
- No row-level security at MySQL level
- Tenant scoping is entirely at application layer (service functions)
- A bug in a service function could expose cross-tenant data

---

## Quiz Status Machine

Transitions provable from service code:

```
DRAFT → READY      (via publish_quiz() — requires at least 1 question)
READY → DRAFT      (via unpublish_quiz())
READY → ARCHIVED   (NOT DERIVABLE — no archive endpoint found in reviewed routes)
DRAFT → (deleted)  (via delete_quiz())
```

- Questions can ONLY be added/updated/deleted when `quiz.status == DRAFT`
- Source: `features/quiz/question_service_async.py` guard check

---

## Session Status Machine

Transitions from `SessionServiceAsync`:

```
CREATED → ACTIVE   (on first advance_question() call)
ACTIVE  → ENDED    (on end_session())
```

- `current_question_index` starts at `-1` (pre-question state)
- Each `advance_question()` increments index; each `back_question()` decrements
- `QuestionStatus`: PENDING → OPEN (on advance) → CLOSED (on next advance or end)
- Source: `features/quiz/session_service_async.py`

---

## Proctoring Invariants

1. **Proctoring config is cached**: `proctor:rules:{quiz_id}:{hash}` in Redis — 1h TTL. Changes to platform rules or tenant policies do NOT propagate to active sessions for up to 1 hour.

2. **Lock is idempotent**: `_check_escalation()` checks `if redis_data.get("is_locked"): return immediately`. Source: `features/proctoring/proctoring_service_async.py:log_violation()`

3. **Lock is permanent until admin unlock**: Once `is_locked=True` in Redis, only `unlock_session()` (admin endpoint) can clear it. Source: `features/proctoring/proctoring_service_async.py:unlock_session()`

4. **Proctoring session is idempotent**: `init_session()` checks for existing `ProctoringSession` for `(participant_id, quiz_id)` and returns existing if found. Source: `features/proctoring/proctoring_service_async.py:init_session()`

5. **Exam content blocked until proctoring config confirmed**: `ProctoringProvider` renders spinner until `ruleSet` state is non-null. Source: `frontend/src/features/proctoring/ProctoringProvider.jsx:93`

6. **Fullscreen is a hard gate**: `FullscreenGate` never renders `children` unless `document.fullscreenElement` is truthy. Source: `frontend/src/features/proctoring/ProctoringGate.jsx:94` — `if (state === 'active') return children`

---

## Participant Token Invariants

1. **Token is globally unique**: `UNIQUE` constraint on `participants.session_token`
2. **Token generated server-side**: `secrets.token_urlsafe()` in Python — cryptographically random
3. **Token cached in Redis**: Fast-path lookup at `session_token:{token}` avoids DB query on every answer submission
4. **Token invalidated on restart**: When session is restarted, `is_active` flag in Redis cache is set to `false` — subsequent answer submits return 403

---

## Email Verification Invariant

- Users with `is_email_verified=False` CANNOT log in (raises `EmailNotVerifiedError` → 403)
- Exception: `demo@swaya.me` bypasses verification check
- Source: `core/auth/service_async.py:login_user()` lines 208-213
- OAuth-registered users bypass verification: `is_email_verified=True` set at creation — Source: `service_async.py:oauth_login_or_register()`
