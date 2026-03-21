# Multi-Tenant Tier System - Complete Documentation Index

## Overview

This is the complete documentation for integrating a **multi-tenant SaaS pricing tier system** (Slido-like) into Swaya.me. All documents follow the existing architecture patterns and maintain the 3-layer model.

**Created:** January 30, 2026  
**Status:** Ready for implementation  
**Technology Stack:** 100% Open Source (FastAPI, SQLAlchemy, MySQL, Redis)

---

## Documentation Map

### 📚 High-Level Vision & Strategy

| Document | Location | Purpose |
|----------|----------|---------|
| **Pricing Tiers** | [Docs/pricing-tiers.md](../../Docs/pricing-tiers.md) | Strategic tier design, feature matrix, pricing model |
| **Multi-Tenant Migration** | [Docs/multi-tenant-migration.md](../../Docs/multi-tenant-migration.md) | Complete migration guide from single to multi-tenant |
| **Multi-Tenant SaaS Architecture (Overview)** | [specs/overview/multi-tenant-saas-architecture.md](../overview/multi-tenant-saas-architecture.md) | High-level architecture overview, enforcement flow |

### 🏗️ Architecture & Design

| Document | Location | Purpose |
|----------|----------|---------|
| **Logical Architecture** | [specs/architecture/logical-architecture.md](../architecture/logical-architecture.md) | Updated 3-layer model with tier enforcement |
| **MVP Scope** | [specs/overview/mvp-scope.md](../overview/mvp-scope.md) | Updated scope with multi-tenant foundation |

### 🛠️ Backend Implementation

| Document | Location | Purpose |
|----------|----------|---------|
| **Tier Management** | [specs/backend/tier-management.md](../backend/tier-management.md) | Implementation details: Services, middleware, quota patterns |
| **Tier Configuration** | [specs/backend/tier-configuration.md](../backend/tier-configuration.md) | Tier definitions, feature gates, quota types |
| **Multi-Tenant Isolation** | [specs/backend/multi-tenant-isolation.md](../backend/multi-tenant-isolation.md) | Data isolation strategy, query scoping, security |
| **Domain Model** | [specs/backend/domain-model.md](../backend/domain-model.md) | Updated entities with tenant_id scoping |

### 🔧 Copilot Instructions

| Document | Location | Updates |
|----------|----------|---------|
| **Copilot Instructions** | [.github/copilot-instructions.md](./.github/copilot-instructions.md) | Added tier enforcement rules and references |

---

## Quick Reference: Key Concepts

### Tier Hierarchy

```
FREE ← 50 participants, 10 questions, MCQ only
  ↓
BASIC ← 100 participants, 25 questions, MCQ + Polls, data export
  ↓
PRO ← 1,000 participants, 100 questions, all features, custom branding
  ↓
ENTERPRISE ← Unlimited everything, SSO, custom support
```

### Architecture Integration

```
Services (API/Realtime)
    ↓ (translate client intent)
Broker Layer [TIER GATES HERE] ← Feature gates, quota checks
    ↓ (validate and route)
Platform Kernel
    ↓ (orchestrate and consume)
Features Layer (Quiz, etc.)
    ↓ (business logic, tier-agnostic)
Persistence (Tenant-scoped queries)
```

### Policy Enforcement (Broker Layer)

1. **Tenant Context Middleware** → Extract tenant once, cache in request.state
2. **Feature Gate Check** → Does tier include this feature?
3. **Quota Check** → Is tenant within limits?
4. **Rate Limit Check** → Per-IP, per-session throttles
5. **Route to Feature** → If all checks pass

### Data Isolation Pattern

```python
# Every table has tenant_id
CREATE TABLE quizzes (
  quiz_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,  # ← Every row scoped to tenant
  ...
);

# Every query includes tenant filter
SELECT * FROM quizzes 
WHERE tenant_id = ? AND quiz_id = ?

# Enforced at all layers
# - Database (composite index on tenant_id)
# - ORM (models inherit from TenantScoped)
# - Middleware (attaches tenant_id to request)
```

---

## Implementation Sequence

### Phase 1: Foundation (Core Services)

**Estimated effort:** 1-2 weeks

```
Step 1: Create database tables
  - tenants, tier_configs, usage_quotas
  - Add tenant_id to all domain tables

Step 2: Implement Core services
  - TenantService (resolve tenant by ID/slug)
  - TierService (load and cache tier configs)
  - EntitlementService (check feature access, verify quotas)

Step 3: Add Broker middleware
  - TenantContextMiddleware (resolve tenant once)
  - TierPolicyEnforcement (check gates and quotas)

Step 4: Update Features
  - Pass tenant_id as parameter
  - Scope all queries to tenant
```

### Phase 2: Enforcement (Feature Gates & UI)

**Estimated effort:** 1 week

```
Step 5: Add feature gate checks
  - custom_branding, data_export, API access, etc.

Step 6: Update frontend
  - Show/hide features based on tier
  - Display "Upgrade required" messages

Step 7: Implement quota consumption
  - After participant join
  - After question add
  - After event start
```

### Phase 3: Monitoring & Analytics

**Estimated effort:** Few days

```
Step 8: Add quota tracking dashboards
  - Tenant quota status
  - Tier distribution
  - Upgrade conversion metrics

Step 9: Implement alerting
  - High quota utilization (>80%)
  - Tier restriction patterns
```

---

## File Organization

### Docs Folder (High-Level Strategy)

```
Docs/
├── pricing-tiers.md           ← Tier design, feature matrix
├── multi-tenant-migration.md  ← Migration guide, SQL scripts
├── logical_architecture.md    ← 3-layer model (UPDATED)
├── mvp-features.md            ← MVP scope (UPDATED)
└── 000_scope.md               ← Architecture constraints (UPDATED)
```

### Specs Folder (Detailed Implementation)

```
specs/
├── overview/
│   ├── mvp-scope.md                          ← MVP scope (UPDATED)
│   └── multi-tenant-saas-architecture.md     ← Tier architecture overview
├── architecture/
│   └── logical-architecture.md               ← 3-layer model (UPDATED)
└── backend/
    ├── domain-model.md                       ← Entities (UPDATED)
    ├── tier-management.md                    ← Implementation details
    ├── tier-configuration.md                 ← Tier definitions
    └── multi-tenant-isolation.md             ← Data isolation strategy
```

---

## Key Design Decisions

### 1. Policy Enforcement in Broker Layer

**Rationale:** Tier checks happen BEFORE feature execution, not inside features.

```
✅ DO: Check in Broker, before routing
❌ DON'T: Check inside feature
❌ DON'T: Have features decide tier limits
```

### 2. Tenant Context Resolved Once Per Request

**Rationale:** Avoid repeated tenant lookups, cache in request.state.

```
✅ DO: Middleware resolves tenant once, cache in request.state.tenant
❌ DON'T: Resolve tenant in every endpoint
❌ DON'T: Pass tenant around function calls
```

### 3. Every Table Scoped by tenant_id

**Rationale:** Cross-tenant data access is a critical security bug.

```
✅ DO: Every table has tenant_id column
✅ DO: Every query includes WHERE tenant_id = ?
❌ DON'T: Rely on auth token to scope data
❌ DON'T: Trust frontend to provide correct tenant
```

### 4. Database-Driven Tier Configuration

**Rationale:** Update tiers without code changes.

```
✅ DO: Store tier configs in tier_configs table (JSON limits/features)
✅ DO: Load at startup, cache in memory
❌ DON'T: Hardcode limits in Python constants
❌ DON'T: Require code deploy for tier changes
```

### 5. Features are Tier-Agnostic

**Rationale:** Features don't know about tiers, Platform enforces limits externally.

```
✅ DO: Feature receives tenant_id as parameter
✅ DO: Feature's quota checked before invocation
❌ DON'T: Feature asks "am I allowed to do this?"
❌ DON'T: Feature enforces its own limits
```

---

## Database Schema Summary

### New Tables

```sql
-- Tenants (organizations)
CREATE TABLE tenants (
  tenant_id UUID PRIMARY KEY,
  name VARCHAR(255),
  slug VARCHAR(100) UNIQUE,
  subscription_tier ENUM('FREE', 'BASIC', 'PRO', 'ENTERPRISE'),
  subscription_status ENUM('ACTIVE', 'TRIAL', 'SUSPENDED', 'CANCELLED')
);

-- Tier configurations (global, not per-tenant)
CREATE TABLE tier_configs (
  tier_id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100),
  limits JSON,           # {"max_participants_per_event": 1000, ...}
  features JSON,         # {"custom_branding": true, ...}
  is_active BOOLEAN
);

-- Usage quotas (per-tenant, per-quota-type)
CREATE TABLE usage_quotas (
  quota_id UUID PRIMARY KEY,
  tenant_id UUID FOREIGN KEY,
  quota_type ENUM('PARTICIPANTS', 'QUESTIONS', 'EVENTS', 'API_CALLS', 'STORAGE', 'EXPORTS'),
  period_start TIMESTAMP,
  period_end TIMESTAMP,
  quota_limit INT,
  consumed INT
);
```

### Modified Tables

All domain tables add `tenant_id` column:
- users (add tenant_id, make email unique per tenant)
- quizzes (add tenant_id)
- quiz_sessions (add tenant_id)
- participants (add tenant_id)
- questions (inherit from quiz)
- options (inherit from question)
- submissions (inherit from session)

---

## Testing Strategy

### Unit Tests

```python
# Test quota calculation
async def test_quota_enforcement():
    tenant = create_test_tenant(tier="FREE")
    # Should allow 50 participants
    # Should reject 51st
    
# Test tier restrictions
async def test_free_tier_cannot_export():
    # FREE tier doesn't have data_export feature
    # Should return 403
```

### Integration Tests

```python
# Test tenant isolation
async def test_tenant_data_isolation():
    tenant1, tenant2 = create_two_tenants()
    quiz1 = create_quiz(tenant1.id, "Secret Quiz")
    
    # Tenant1 can see own quiz
    # Tenant2 gets 404
    
# Test policy enforcement
async def test_free_tier_participant_limit():
    # Free tier = 50 participants
    # 51st join should be rejected with upgrade CTA
```

### E2E Tests

```python
# Test upgrade flow
async def test_free_to_pro_upgrade():
    tenant = create_tenant(tier="FREE")
    
    # Export fails (not in Free tier)
    response = await client.post("/api/quiz/export")
    assert response.status_code == 403
    
    # Upgrade to PRO
    await upgrade_tenant(tenant.id, "PRO")
    
    # Export succeeds
    response = await client.post("/api/quiz/export")
    assert response.status_code == 200
```

---

## Monitoring & Alerts

### Key Metrics

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| Quota Utilization | Identify upgrade candidates | >80% of limit |
| Tier Restriction Rate | UX issue? Feature not discoverable? | >10% of requests |
| Quota Exceeded Rate | Capacity planning | >5% of requests |
| Tier Distribution | Revenue forecasting | N/A |
| Upgrade Conversion | Product optimization | <2% (upgrade CTA not working) |

### Sample Queries

```sql
-- High quota utilization (upgrade candidates)
SELECT tenant_id, quota_type, consumed, quota_limit 
FROM usage_quotas 
WHERE (consumed::float / quota_limit) > 0.8;

-- Tier distribution
SELECT subscription_tier, COUNT(*) as count 
FROM tenants 
GROUP BY subscription_tier;

-- Quota exceeded events
SELECT COUNT(*) FROM audit_logs 
WHERE event = 'quota_exceeded' 
GROUP BY tenant_id 
ORDER BY COUNT(*) DESC;
```

---

## Security Checklist

Before deploying multi-tenant system:

- [ ] Audit all database queries for tenant_id filter
- [ ] Verify no raw SQL queries without tenant scoping
- [ ] Test cross-tenant data access (should return 404)
- [ ] Verify tenant context middleware on all routes
- [ ] Check email uniqueness per tenant (not global)
- [ ] Verify quota enforcement before feature execution
- [ ] Load test quota consumption under high traffic
- [ ] Review audit logs for security incidents
- [ ] Penetration test multi-tenant boundaries

---

## Support & Questions

### Architecture Clarifications
- See [specs/overview/multi-tenant-saas-architecture.md](../overview/multi-tenant-saas-architecture.md)
- See [specs/architecture/logical-architecture.md](../architecture/logical-architecture.md)

### Implementation Details
- Tier enforcement: [specs/backend/tier-management.md](../backend/tier-management.md)
- Data isolation: [specs/backend/multi-tenant-isolation.md](../backend/multi-tenant-isolation.md)
- Tier config: [specs/backend/tier-configuration.md](../backend/tier-configuration.md)

### Database Changes
- Schema changes: [Docs/multi-tenant-migration.md](../../Docs/multi-tenant-migration.md)
- SQL scripts: See "Data Migration Steps" in multi-tenant-migration.md

### Development Environment
- Seed tier configs: See "Tier Configuration Source" in tier-configuration.md
- Test fixture setup: See specs/qa/fixtures.md (to be updated)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-30 | Initial multi-tenant tier system design (MVP foundation) |

---

## Next Action

1. Review all documentation (start with [multi-tenant-saas-architecture.md](../overview/multi-tenant-saas-architecture.md))
2. Run database migrations (scripts in [Docs/multi-tenant-migration.md](../../Docs/multi-tenant-migration.md))
3. Implement Core services ([tier-management.md](../backend/tier-management.md) implementation section)
4. Add middleware ([tier-management.md](../backend/tier-management.md) Broker Layer section)
5. Update features to receive tenant_id
6. Test tenant isolation ([multi-tenant-isolation.md](../backend/multi-tenant-isolation.md) testing section)

**Happy coding! 🚀**
