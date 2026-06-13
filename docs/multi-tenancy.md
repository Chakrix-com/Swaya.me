# Multi-Tenancy

Swaya is a multi-tenant platform: a single deployment serves many independent organizations (tenants). Each tenant has isolated data, its own users, and tier-based usage limits.

---

## Isolation Model

**Shared database, tenant-scoped rows** — all tenants use the same MySQL database, but every application record carries a `tenant_id` foreign key. No cross-tenant data access is possible without explicitly bypassing the tenant filter, which service functions never do.

```sql
-- Every core table follows this pattern:
CREATE TABLE quiz (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    tenant_id   INT NOT NULL REFERENCES tenant(id),
    title       VARCHAR(255) NOT NULL,
    ...
    INDEX (tenant_id)
);
```

Tables with `tenant_id`: `user`, `quiz`, `quiz_session`, `question`, `question_option`, `participant`, `answer`, `proctoring_snapshot`, `platform_event`, `app_feedback`, `tier_config`, `refresh_token_jti`.

---

## How tenant_id Flows Through a Request

1. User logs in → FastAPI issues a JWT containing `tenant_id` and `user_id` claims.
2. Every subsequent request sends this JWT (cookie or Bearer header).
3. `get_current_user` dependency (`core/auth/dependencies.py`) decodes the JWT and returns a `CurrentUser` named tuple with `tenant_id`, `user_id`, `role`.
4. The tenant isolation middleware (`broker/policies/tenant_isolation.py`) validates the `tenant_id` is present.
5. Service functions receive `current_user.tenant_id` and apply it as a WHERE filter on every query:

```python
result = await db.execute(
    select(Quiz).where(
        Quiz.id == quiz_id,
        Quiz.tenant_id == current_user.tenant_id,  # isolation filter
    )
)
```

A quiz from tenant 2 is simply not found when requested by a user from tenant 1 — the query returns nothing, and a 404 is raised.

---

## Tenant Registration

Tenants are created by `super_admin` users (tenant_id=1). The registration flow:
1. `super_admin` calls `POST /api/v1/admin/tenants` with the organization name and initial admin email.
2. FastAPI creates a `Tenant` row and an `admin` user linked to it.
3. The tenant admin can then invite additional users.

---

## Roles

| Role | Scope | Capabilities |
|---|---|---|
| `super_admin` | Platform-wide (tenant_id=1 only) | Manage all tenants, platform config, tier assignment |
| `admin` | Own tenant | Manage users, view all quizzes, trigger emails, AI analysis |
| `user` | Own tenant | Create and run quizzes/exams, view own results |
| `viewer` | Own tenant | Read-only access to results and dashboards |

Role is stored in the `user.role` column (enum) and included in the JWT `role` claim. FastAPI dependencies enforce it:

```python
# Only admin or super_admin can call this endpoint:
current_user: CurrentUser = Depends(require_admin)

# Only super_admin:
current_user: CurrentUser = Depends(require_super_admin)
```

---

## Tier System

Each tenant is assigned a tier: `FREE`, `BASIC`, `PRO`, or `ENTERPRISE`. Tier limits control:

| Limit | Description |
|---|---|
| `max_participants` | Maximum audience size per live session |
| `max_questions` | Maximum questions per quiz |
| `max_concurrent_sessions` | How many live sessions can run simultaneously |
| `features` | JSON blob of enabled feature flags (e.g., proctoring, AI, export) |

### Enforcement

`TierService` (`core/config/tier_service.py`) is called at the start of any action that consumes a limit. It:
1. Looks up the tenant's `TierConfig` from Redis (5-minute cache).
2. Falls back to MySQL if not cached.
3. Raises `TierLimitError` if the action would exceed the limit.
4. FastAPI routes map `TierLimitError` to HTTP 403.

The cache TTL means a tier upgrade takes effect within 5 minutes without a server restart.

### Default Limits (FREE tier)

| Limit | Value |
|---|---|
| `max_participants` | 50 |
| `max_questions` | 10 |
| `max_concurrent_sessions` | 1 |

Higher tiers are configured per-tenant in the `tier_config` table (not hard-coded), so limits can be customized per customer.

---

## Public (Unauthenticated) Endpoints

Some endpoints are intentionally public — audience members never log in:

| Endpoint | Who calls it |
|---|---|
| `GET /api/v1/join/{code}` | Audience joining a live quiz |
| `POST /api/v1/e/{slug}/request-otp` | Exam participant requesting OTP |
| `POST /api/v1/e/{slug}/start` | Exam participant starting with OTP |
| `POST /api/v1/e/{slug}/answer` | Exam participant saving an answer |
| `POST /api/v1/e/{slug}/submit` | Exam participant submitting |
| `POST /api/v1/e/{slug}/result` | Exam participant viewing their own result |
| `GET /api/v1/events/session/{id}` | SSE stream for audience |

These endpoints authenticate the *participant* via a `session_token` (opaque, issued at exam start and stored in Redis), not a JWT. The `session_token` is scoped to a single exam participation. There is no way to use it to access another tenant's data.

---

## Tenant Branding

Each tenant can configure:
- Organization name (shown in UI and emails)
- Logo image (uploaded via the image upload API)
- Theme (color palette via CSS custom properties)

Branding is resolved from the authenticated user's tenant at render time — no subdomain routing is required.
