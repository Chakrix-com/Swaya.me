# Multi-Tenant Migration Guide

## Overview

This guide describes the migration from a single-tenant to a multi-tenant architecture with tier-based pricing.

---

## Database Schema Changes

### New Tables

#### 1. `tenants` table

```sql
CREATE TABLE tenants (
    tenant_id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    subscription_tier ENUM('FREE', 'BASIC', 'PRO', 'ENTERPRISE') NOT NULL DEFAULT 'FREE',
    subscription_status ENUM('ACTIVE', 'TRIAL', 'SUSPENDED', 'CANCELLED') NOT NULL DEFAULT 'TRIAL',
    subscription_start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subscription_end TIMESTAMP NULL,
    billing_cycle ENUM('MONTHLY', 'ANNUAL', 'CUSTOM') NOT NULL DEFAULT 'MONTHLY',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_slug (slug),
    INDEX idx_subscription_status (subscription_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 2. `tier_configs` table

```sql
CREATE TABLE tier_configs (
    tier_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    limits JSON NOT NULL,
    features JSON NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 3. `usage_quotas` table

```sql
CREATE TABLE usage_quotas (
    quota_id CHAR(36) PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    quota_type ENUM('PARTICIPANTS', 'QUESTIONS', 'EVENTS', 'API_CALLS', 'STORAGE', 'EXPORTS') NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    quota_limit INT NOT NULL,
    consumed INT NOT NULL DEFAULT 0,
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    INDEX idx_tenant_quota (tenant_id, quota_type),
    INDEX idx_period (period_start, period_end),
    
    CONSTRAINT chk_consumed_within_limit CHECK (consumed <= quota_limit)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Modified Tables (Add tenant_id)

#### 1. `users` table

```sql
ALTER TABLE users
ADD COLUMN tenant_id CHAR(36) NOT NULL AFTER user_id,
ADD COLUMN role ENUM('OWNER', 'ADMIN', 'MEMBER') NOT NULL DEFAULT 'MEMBER' AFTER display_name,
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER role,
ADD FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
DROP INDEX idx_email,
ADD INDEX idx_tenant_email (tenant_id, email),
ADD CONSTRAINT uq_tenant_email UNIQUE (tenant_id, email);
```

#### 2. `quizzes` table

```sql
ALTER TABLE quizzes
ADD COLUMN tenant_id CHAR(36) NOT NULL AFTER quiz_id,
ADD FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
ADD INDEX idx_tenant_quiz (tenant_id, quiz_id);
```

#### 3. `quiz_sessions` table

```sql
ALTER TABLE quiz_sessions
ADD COLUMN tenant_id CHAR(36) NOT NULL AFTER session_id,
ADD FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
ADD INDEX idx_tenant_session (tenant_id, session_id);
```

---

## Data Migration Steps

### Step 1: Create Default Tenant

```sql
-- Create a default tenant for existing data
INSERT INTO tenants (tenant_id, name, slug, subscription_tier, subscription_status)
VALUES (
    UUID(),
    'Default Organization',
    'default',
    'PRO',  -- Give generous tier during migration
    'ACTIVE'
);

-- Store tenant_id for next steps
SET @default_tenant_id = (SELECT tenant_id FROM tenants WHERE slug = 'default');
```

### Step 2: Seed Tier Configurations

```sql
INSERT INTO tier_configs (tier_id, name, limits, features) VALUES
(
    'FREE',
    'Free',
    JSON_OBJECT(
        'max_participants_per_event', 50,
        'max_questions_per_quiz', 10,
        'max_concurrent_events', 1,
        'max_team_members', 1,
        'event_history_days', 7,
        'storage_mb', 100,
        'api_calls_per_hour', 100,
        'exports_per_day', 0
    ),
    JSON_OBJECT(
        'quiz_types', JSON_ARRAY('mcq'),
        'custom_branding', FALSE,
        'branding_removal', FALSE,
        'moderation_queue', FALSE,
        'data_export', FALSE,
        'api_access', 'none',
        'sso_enabled', FALSE,
        'webhook_enabled', FALSE,
        'profanity_mode', 'reject'
    )
),
(
    'BASIC',
    'Basic',
    JSON_OBJECT(
        'max_participants_per_event', 100,
        'max_questions_per_quiz', 25,
        'max_concurrent_events', 3,
        'max_team_members', 3,
        'event_history_days', 30,
        'storage_mb', 1000,
        'api_calls_per_hour', 1000,
        'exports_per_day', 10
    ),
    JSON_OBJECT(
        'quiz_types', JSON_ARRAY('mcq', 'poll'),
        'custom_branding', FALSE,
        'branding_removal', FALSE,
        'moderation_queue', FALSE,
        'data_export', TRUE,
        'api_access', 'none',
        'sso_enabled', FALSE,
        'webhook_enabled', FALSE,
        'profanity_mode', 'configurable'
    )
),
(
    'PRO',
    'Professional',
    JSON_OBJECT(
        'max_participants_per_event', 1000,
        'max_questions_per_quiz', 100,
        'max_concurrent_events', 10,
        'max_team_members', 10,
        'event_history_days', 365,
        'storage_mb', 5000,
        'api_calls_per_hour', 10000,
        'exports_per_day', 50
    ),
    JSON_OBJECT(
        'quiz_types', JSON_ARRAY('mcq', 'poll', 'word_cloud', 'survey'),
        'custom_branding', TRUE,
        'branding_removal', TRUE,
        'moderation_queue', TRUE,
        'data_export', TRUE,
        'api_access', 'readonly',
        'sso_enabled', FALSE,
        'webhook_enabled', TRUE,
        'profanity_mode', 'configurable'
    )
),
(
    'ENTERPRISE',
    'Enterprise',
    JSON_OBJECT(
        'max_participants_per_event', -1,  -- unlimited
        'max_questions_per_quiz', -1,
        'max_concurrent_events', -1,
        'max_team_members', -1,
        'event_history_days', -1,
        'storage_mb', 50000,
        'api_calls_per_hour', 100000,
        'exports_per_day', -1
    ),
    JSON_OBJECT(
        'quiz_types', JSON_ARRAY('mcq', 'poll', 'word_cloud', 'survey', 'custom'),
        'custom_branding', TRUE,
        'branding_removal', TRUE,
        'moderation_queue', TRUE,
        'data_export', TRUE,
        'api_access', 'full',
        'sso_enabled', TRUE,
        'webhook_enabled', TRUE,
        'profanity_mode', 'configurable'
    )
);
```

### Step 3: Migrate Existing Data

```sql
-- Update users with default tenant
UPDATE users SET tenant_id = @default_tenant_id;

-- Update quizzes with default tenant
UPDATE quizzes SET tenant_id = @default_tenant_id;

-- Update quiz_sessions with default tenant
UPDATE quiz_sessions SET tenant_id = @default_tenant_id;
```

### Step 4: Initialize Quotas

```sql
-- Create initial quota tracking for default tenant
INSERT INTO usage_quotas (quota_id, tenant_id, quota_type, period_start, period_end, quota_limit, consumed)
SELECT 
    UUID(),
    @default_tenant_id,
    'PARTICIPANTS',
    DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00'),
    LAST_DAY(NOW()) + INTERVAL 1 SECOND - INTERVAL 1 SECOND,
    1000,  -- PRO tier limit
    0
FROM DUAL;

-- Repeat for other quota types (QUESTIONS, EVENTS, etc.)
```

---

## Application Layer Changes

### Core Layer: New Services

#### 1. Tenant Service (`backend/core/tenant_service.py`)

```python
class TenantService:
    async def get_tenant_by_id(self, tenant_id: UUID) -> Tenant:
        """Retrieve tenant by ID"""
        
    async def get_tenant_by_slug(self, slug: str) -> Tenant:
        """Retrieve tenant by slug"""
        
    async def get_tenant_tier_config(self, tenant_id: UUID) -> TierConfig:
        """Get active tier configuration for tenant"""
        
    async def create_tenant(self, name: str, slug: str, tier: str) -> Tenant:
        """Create new tenant (signup flow)"""
```

#### 2. Entitlement Service (`backend/core/entitlement_service.py`)

```python
class EntitlementService:
    async def check_feature_access(self, tenant_id: UUID, feature: str) -> bool:
        """Check if tenant's tier includes feature"""
        
    async def check_quota_available(
        self, 
        tenant_id: UUID, 
        quota_type: QuotaType, 
        amount: int = 1
    ) -> bool:
        """Check if tenant has available quota"""
        
    async def consume_quota(
        self, 
        tenant_id: UUID, 
        quota_type: QuotaType, 
        amount: int = 1
    ) -> None:
        """Increment quota consumption"""
        
    async def release_quota(
        self, 
        tenant_id: UUID, 
        quota_type: QuotaType, 
        amount: int = 1
    ) -> None:
        """Decrement quota consumption (e.g., participant leaves)"""
        
    async def get_quota_status(self, tenant_id: UUID) -> dict[QuotaType, QuotaStatus]:
        """Get current quota utilization for all types"""
```

### Broker Layer: Enhanced Policy Enforcement

#### Updated Request Flow (`backend/broker/middleware.py`)

```python
@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    """
    Extract and validate tenant context for every request.
    Executed ONCE per request, cached in request.state
    """
    # Extract tenant identifier from JWT or session token
    tenant_id = await extract_tenant_id(request)
    
    # Load tenant context (with caching)
    tenant_context = await load_tenant_context(tenant_id)
    
    # Validate subscription status
    if tenant_context.subscription_status != SubscriptionStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Subscription inactive")
    
    # Attach to request state
    request.state.tenant = tenant_context
    
    response = await call_next(request)
    return response


async def enforce_tier_policies(request: Request):
    """
    Enforce tier-based feature gates and quota limits.
    Called BEFORE routing to features.
    """
    tenant = request.state.tenant
    action = request.url.path  # or extract from route metadata
    
    # Check feature access
    if not await entitlement_service.check_feature_access(tenant.id, action):
        raise TierRestrictionError(
            message=f"Feature requires upgrade",
            current_tier=tenant.tier,
            required_tier="PRO"
        )
    
    # Check quotas (if applicable to action)
    quota_type = get_quota_type_for_action(action)
    if quota_type and not await entitlement_service.check_quota_available(tenant.id, quota_type):
        raise QuotaExceededError(
            message=f"Quota limit reached",
            quota_type=quota_type,
            limit=tenant.limits[quota_type]
        )
```

### Feature Layer: No Changes Required

Features remain tenant-agnostic. Tenant context is provided by Platform, not resolved by features.

---

## Testing Strategy

### Unit Tests

```python
# Test tier configuration loading
def test_load_tier_config():
    config = load_tier_config("PRO")
    assert config.limits["max_participants_per_event"] == 1000

# Test quota enforcement
async def test_quota_enforcement():
    tenant = create_test_tenant(tier="FREE")
    
    # Should allow within limit
    for i in range(50):
        assert await check_quota_available(tenant.id, "PARTICIPANTS")
    
    # Should reject when limit reached
    assert not await check_quota_available(tenant.id, "PARTICIPANTS")
```

### Integration Tests

```python
# Test tenant isolation
async def test_tenant_data_isolation():
    tenant1 = create_tenant("Org1")
    tenant2 = create_tenant("Org2")
    
    quiz1 = create_quiz(tenant1.id, "Quiz 1")
    quiz2 = create_quiz(tenant2.id, "Quiz 2")
    
    # Tenant1 should not see Tenant2's quiz
    quizzes = await get_quizzes(tenant1.id)
    assert quiz1 in quizzes
    assert quiz2 not in quizzes
```

### E2E Tests

```python
# Test tier restriction UX
async def test_tier_restriction_flow():
    # Login as FREE tier user
    client = create_authenticated_client(tier="FREE")
    
    # Attempt to access PRO feature
    response = await client.post("/api/quiz/export")
    
    # Should return 403 with upgrade CTA
    assert response.status_code == 403
    assert "upgrade" in response.json()["upgrade_url"]
```

---

## Rollback Plan

If migration fails:

```sql
-- Remove tenant_id columns
ALTER TABLE users DROP FOREIGN KEY users_ibfk_tenant;
ALTER TABLE users DROP COLUMN tenant_id, DROP COLUMN role, DROP COLUMN is_active;

ALTER TABLE quizzes DROP FOREIGN KEY quizzes_ibfk_tenant;
ALTER TABLE quizzes DROP COLUMN tenant_id;

ALTER TABLE quiz_sessions DROP FOREIGN KEY quiz_sessions_ibfk_tenant;
ALTER TABLE quiz_sessions DROP COLUMN tenant_id;

-- Drop new tables
DROP TABLE usage_quotas;
DROP TABLE tier_configs;
DROP TABLE tenants;

-- Restore original unique constraint on users.email
ALTER TABLE users ADD UNIQUE INDEX idx_email (email);
```

---

## Post-Migration Checklist

- [ ] All existing data assigned to default tenant
- [ ] Tier configurations seeded
- [ ] Quota tracking initialized
- [ ] Tenant context middleware active
- [ ] Policy enforcement functional
- [ ] Feature gates tested
- [ ] Multi-tenant data isolation verified
- [ ] Admin can create new tenants
- [ ] Signup flow creates new tenants
- [ ] Billing integration ready (if applicable)

---

## Performance Considerations

### Caching Strategy

```python
# Cache tier configs in memory (rarely change)
tier_config_cache = TTLCache(maxsize=100, ttl=3600)

# Cache tenant context in Redis (5-minute TTL)
@cached(cache=redis_cache, key="tenant:{tenant_id}", ttl=300)
async def load_tenant_context(tenant_id: UUID) -> TenantContext:
    ...
```

### Query Optimization

```sql
-- Add composite indexes for tenant-scoped queries
CREATE INDEX idx_tenant_created ON quizzes(tenant_id, created_at);
CREATE INDEX idx_tenant_status ON quiz_sessions(tenant_id, status);
```

---

## Summary

This migration transforms the application from single-tenant to multi-tenant SaaS with:

1. **Tenant isolation** at database and application layers
2. **Configurable tier-based limits** stored in database
3. **Quota tracking and enforcement** before feature execution
4. **Zero changes to Feature layer** (tenant-agnostic by design)

The architecture preserves the 3-layer model while adding horizontal tenant scaling.
