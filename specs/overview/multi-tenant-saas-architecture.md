# Multi-Tenant SaaS Architecture (Tier System Overview)

## Overview

This document provides a high-level summary of the multi-tenant, tier-based SaaS architecture for Swaya.me.

The system is designed as a **modular monolith** with clear 3-layer separation, where:
- **Core Layer** manages identity, tenancy, and tier configuration
- **Broker Layer** enforces tier policies and quotas before routing
- **Features Layer** remains tier-agnostic and tenant-unaware

---

## Architectural Layers

### 1. Services Layer (Transport)
- API Service (REST endpoints)
- Realtime Service (WebSocket/SSE)
- **Responsibility:** Handle I/O only
- **Tier Awareness:** None (policies applied by Broker)

### 2. Broker Layer (Policy Enforcement)
- **Tenant Context Middleware:** Resolve tenant once per request
- **Feature Gate Enforcement:** Check tier allows feature
- **Quota Enforcement:** Check usage within limits
- **Rate Limiting:** Apply per-IP, per-session throttles
- **Authentication:** Verify JWT tokens
- **Profanity Detection:** Check user content (post-MVP)
- **Command Routing:** Validate and route to features
- **Responsibility:** ALL policy checks happen here, BEFORE feature execution

### 3. Platform Kernel (Orchestration)
- Calls appropriate features with tenant context
- Consumes quotas AFTER successful feature execution
- Logs audit events
- Manages session lifecycle

### 4. Features Layer (Business Logic)
- Quiz feature (MVP)
- Future: Polls, Word Cloud, Q&A, etc.
- **Responsibility:** Business logic only
- **Tier Awareness:** None
- **Tenant Awareness:** Receives tenant_id as parameter, doesn't resolve it

---

## Data Isolation Strategy

```
Request → Middleware extracts tenant_id from JWT/session
          ↓
          Attach to request.state.tenant
          ↓
          All database queries include: WHERE tenant_id = ?
          ↓
          Feature receives tenant_id as parameter
          ↓
          Feature's queries are automatically scoped
          ↓
          Response sent (contains only tenant's data)
```

**Key Principle:** Tenant ID flows through entire request context.

Every table has `tenant_id` column:
- Quiz has tenant_id
- QuizSession has tenant_id
- Participant has tenant_id
- Questions, Options, Submissions all have tenant_id (via inheritance)

---

## Tier Structure (Slido-Like)

| Tier | Participants | Questions | Events | Features | Price |
|------|-------------|-----------|--------|----------|-------|
| **Free** | 50 | 10 | 1 | MCQ only | $0 |
| **Basic** | 100 | 25 | 3 | MCQ, Polls | $10-15/mo |
| **Pro** | 1,000 | 100 | 10 | MCQ, Polls, Word Cloud, Survey | $25-40/mo |
| **Enterprise** | Unlimited | Unlimited | Unlimited | All + Custom | Custom |

---

## Policy Enforcement Flow

```
Incoming Request
    ↓
[Nginx] ← Edge rate limiting, SSL termination
    ↓
[Tenant Context Middleware] ← Extract tenant_id, resolve tenant config
    ↓
[Feature Gate Enforcement] ← Check tier includes feature
    ↓
[Quota Enforcement] ← Check usage within limit
    ↓
[Rate Limit Enforcement] ← Check per-IP/per-session throttles
    ↓
[Authentication] ← Verify JWT, role
    ↓
[Command Routing] ← Route to appropriate feature
    ↓
[Feature Execution] ← Feature is tier-agnostic
    ↓
[Quota Consumption] ← Decrement quota
    ↓
Response with upgrade CTAs if tier-restricted
```

---

## Tenant Context Resolution (Once Per Request)

```python
# Step 1: Extract tenant ID
tenant_id = extract_from_jwt(request.headers["Authorization"])

# Step 2: Load tenant config (with Redis caching)
tenant_context = {
  "tenant_id": tenant_id,
  "tier": "PRO",
  "limits": {
    "max_participants_per_event": 1000,
    "max_questions_per_quiz": 100,
    "max_concurrent_events": 10,
    ...
  },
  "features": {
    "custom_branding": true,
    "data_export": true,
    "api_access": "readonly",
    ...
  }
}

# Step 3: Attach to request
request.state.tenant = tenant_context

# Step 4: All downstream code accesses via request.state.tenant
# No need to resolve again
```

---

## Quota Types & Enforcement

### PARTICIPANTS (Per Event)
- **Scope:** Simultaneous participants in quiz session
- **Check:** Before participant joins
- **Consume:** On successful join
- **Release:** When participant leaves
- **Limit:** 50 (Free) → 100 (Basic) → 1,000 (Pro) → Unlimited (Enterprise)

### QUESTIONS (Per Quiz)
- **Scope:** Total questions in a quiz
- **Check:** Before adding question
- **Consume:** On successful question add
- **Limit:** 10 (Free) → 25 (Basic) → 100 (Pro) → Unlimited (Enterprise)

### EVENTS (Concurrent)
- **Scope:** Active quiz sessions per tenant
- **Check:** Before starting quiz
- **Consume:** On session start
- **Release:** On session end
- **Limit:** 1 (Free) → 3 (Basic) → 10 (Pro) → Unlimited (Enterprise)

### STORAGE
- **Scope:** Total database storage per tenant
- **Check:** Before creating large objects
- **Consume:** Automatic based on data size
- **Limit:** 100 MB (Free) → 1 GB (Basic) → 5 GB (Pro) → 50 GB (Enterprise)

### API_CALLS
- **Scope:** API requests per hour
- **Check:** Before processing request
- **Consume:** After successful request
- **Limit:** 100/hr (Free) → 1,000/hr (Basic) → 10,000/hr (Pro) → 100,000/hr (Enterprise)

### EXPORTS
- **Scope:** Data exports per day
- **Check:** Before export operation
- **Consume:** On successful export
- **Limit:** 0/day (Free) → 10/day (Basic) → 50/day (Pro) → Unlimited (Enterprise)

---

## Error Responses

### 403 Forbidden - Tier Restriction

```json
{
  "error": "tier_restriction",
  "message": "This feature requires a Professional plan",
  "details": {
    "feature": "custom_branding",
    "current_tier": "free",
    "required_tier": "pro",
    "upgrade_url": "/pricing?plan=pro&source=custom_branding"
  }
}
```

### 429 Too Many Requests - Quota Exceeded

```json
{
  "error": "quota_exceeded",
  "message": "Participant limit reached (50/50)",
  "details": {
    "quota_type": "participants_per_event",
    "limit": 50,
    "consumed": 50,
    "reset_at": "2026-02-01T00:00:00Z",
    "upgrade_url": "/pricing?plan=basic&source=quota"
  }
}
```

---

## Database Schema (Tenant Scoping)

### Core Tenant Tables

```sql
-- Tenants (organizations)
CREATE TABLE tenants (
  tenant_id UUID PRIMARY KEY,
  name VARCHAR(255),
  slug VARCHAR(100) UNIQUE,
  subscription_tier ENUM('FREE', 'BASIC', 'PRO', 'ENTERPRISE'),
  subscription_status ENUM('ACTIVE', 'TRIAL', 'SUSPENDED', 'CANCELLED')
);

-- Tier configurations (globally defined, not per-tenant)
CREATE TABLE tier_configs (
  tier_id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100),
  limits JSON,
  features JSON,
  is_active BOOLEAN
);

-- Quota tracking (per-tenant, per-quota-type)
CREATE TABLE usage_quotas (
  quota_id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY,
  quota_type ENUM('PARTICIPANTS', 'QUESTIONS', 'EVENTS', 'API_CALLS', 'STORAGE', 'EXPORTS'),
  period_start TIMESTAMP,
  period_end TIMESTAMP,
  quota_limit INT,
  consumed INT
);

-- Users (per-tenant, email unique within tenant)
CREATE TABLE users (
  user_id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY,  -- ← Tenant scope
  email VARCHAR(255),
  UNIQUE (tenant_id, email)   -- ← Email unique per tenant
);

-- Quizzes (per-tenant)
CREATE TABLE quizzes (
  quiz_id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY,  -- ← Tenant scope
  host_id UUID FOREIGN KEY,
  title VARCHAR(255)
);

-- Quiz sessions (per-tenant)
CREATE TABLE quiz_sessions (
  session_id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY,  -- ← Tenant scope
  quiz_id UUID FOREIGN KEY,
  status ENUM('CREATED', 'ACTIVE', 'ENDED')
);

-- Participants (per-tenant, per-session)
CREATE TABLE participants (
  participant_id UUID PRIMARY KEY,
  session_id UUID FOREIGN KEY,
  tenant_id UUID FOREIGN KEY,  -- ← Tenant scope (for isolation)
  display_name VARCHAR(255)
);
```

**Pattern:** Every table that contains user data includes `tenant_id` column. All queries automatically scope by tenant.

---

## Implementation Phases

### Phase 1: MVP (Multi-Tenant Foundation)
- ✅ Database schema with tenant_id on all tables
- ✅ Tenant context middleware
- ✅ TenantService, EntitlementService, TierService
- ✅ Basic tier enforcement (Free, Pro)
- ✅ Quota consumption tracking
- ✅ Participant/question/event limit checks
- ✅ Error responses with upgrade CTAs

### Phase 2: MVP+1 (Feature Gates & UI)
- ☐ Feature gate checks (custom_branding, data_export, etc.)
- ☐ UI updates (show/hide features based on tier)
- ☐ Upgrade flow (Free → Pro, etc.)
- ☐ Admin dashboard (view tier, quotas, users)

### Phase 3: Post-MVP (Monetization)
- ☐ Billing integration (Stripe/Paddle)
- ☐ Trial period management
- ☐ Subscription management UI
- ☐ Usage dashboards
- ☐ Payment retry logic

### Phase 4: V1+ (Enterprise)
- ☐ Custom tier definitions
- ☐ Per-tenant limit overrides
- ☐ SSO/SAML
- ☐ White-label branding
- ☐ API access tier enforcement

---

## Technology Stack (Tier System)

| Component | Purpose | License |
|-----------|---------|---------|
| FastAPI | Request handling and policy middleware | MIT |
| SQLAlchemy 2.0 | ORM with tenant scoping | MIT |
| Redis | Tenant context caching, quota counters | BSD |
| Pydantic | Tier config validation | MIT |
| Python JWT | Tenant extraction from tokens | MIT |
| MySQL | Persistent storage | GPL v2 |

---

## Security Considerations

### Cross-Tenant Access Prevention

1. **Database Level:** Every query includes `WHERE tenant_id = ?`
2. **ORM Level:** SQLAlchemy models inherit from `TenantScoped` base
3. **Application Level:** Middleware enforces tenant context
4. **Audit Level:** All cross-tenant attempts logged as security incidents

### Tenant Context Integrity

1. Tenant ID extracted ONCE per request
2. Cached in Redis (5-minute TTL)
3. Attached to request.state
4. All downstream code uses request.state.tenant
5. Immutable during request lifecycle

### Quota Enforcement

1. Checked BEFORE feature execution
2. Rejected with clear error message + upgrade CTA
3. Consumed AFTER successful operation
4. Logged for analytics and capacity planning

---

## Monitoring & Alerting

### Key Metrics

| Metric | Query | Alert |
|--------|-------|-------|
| Quota Utilization | `consumed/limit * 100` | >80% |
| Tier Distribution | `COUNT(*) per tier` | N/A |
| Tier Restriction Rate | `restrictions / total_requests` | >10% |
| Quota Exceeded Rate | `quota_errors / total_requests` | >5% |
| Upgrade Conversion | `upgrades / restrictions` | <2% |

### Sample Alerts

- **High Quota Utilization:** Alert Pro tier customers at >80% usage
- **High Restriction Rate:** Check if UX is confusing (show upgrade CTA)
- **Low Conversion Rate:** Optimization opportunity (pricing adjustment needed)

---

## Documentation Structure

| Document | Location | Purpose |
|----------|----------|---------|
| **Pricing Tiers** | [Docs/pricing-tiers.md](../../Docs/pricing-tiers.md) | High-level tier design |
| **Multi-Tenant Migration** | [Docs/multi-tenant-migration.md](../../Docs/multi-tenant-migration.md) | Database schema changes |
| **Tier Management** | [specs/backend/tier-management.md](./tier-management.md) | Backend implementation |
| **Multi-Tenant Isolation** | [specs/backend/multi-tenant-isolation.md](./multi-tenant-isolation.md) | Data isolation strategy |
| **Tier Configuration** | [specs/backend/tier-configuration.md](./tier-configuration.md) | Tier definitions & quotas |
| **Logical Architecture** | [specs/architecture/logical-architecture.md](../architecture/logical-architecture.md) | 3-layer model |
| **MVP Scope** | [specs/overview/mvp-scope.md](../overview/mvp-scope.md) | MVP features |

---

## Next Steps

1. ✅ Create database schema (migration scripts in multi-tenant-migration.md)
2. ✅ Implement Core services (TenantService, EntitlementService, TierService)
3. ✅ Add middleware (tenant context, tier enforcement)
4. ✅ Update features to receive tenant_id
5. ✅ Add error handling with upgrade CTAs
6. ☐ Build quota tracking UI
7. ☐ Implement tier upgrade flow
8. ☐ Add analytics and monitoring
9. ☐ Integrate billing (post-MVP)
