# Tier Configuration & Feature Gates

## Overview

This document defines the tier definitions, feature matrix, and quota limits for Swaya.me SaaS tiers.

**Source of Truth:** All tier configurations are stored in the `tier_configs` database table and loaded into memory at application startup.

---

## Tier Definitions

### Tier Hierarchy

```
FREE ← Entry level, limited
  ↓
BASIC ← Growing teams, team collaboration
  ↓
PRO ← Professional users, advanced features
  ↓
ENTERPRISE ← Large organizations, custom setup
```

---

## Complete Feature Matrix

| Feature | Free | Basic | Pro | Enterprise |
|---------|------|-------|-----|------------|
| **Participants per Event** | 50 | 100 | 1,000 | Unlimited |
| **Questions per Quiz** | 10 | 25 | 100 | Unlimited |
| **Concurrent Events** | 1 | 3 | 10 | Unlimited |
| **Event History** | 7 days | 30 days | 365 days | Unlimited |
| **Quiz Types** | MCQ | MCQ, Polls | MCQ, Polls, Word Cloud, Survey | All + Custom |
| **Live Results Display** | Counts | Counts, % | Charts, Export preview | Real-time, Advanced analytics |
| **Branding** | Standard only | Standard only | Remove + Custom | Full white-label |
| **Data Export** | ❌ | CSV/JSON | CSV/JSON, API | CSV/JSON, Full API |
| **Moderation Queue** | ❌ | ❌ | ✅ | ✅ |
| **Team Members** | 1 | 3 | 10 | Unlimited |
| **Profanity Control** | Auto-reject | Configurable | Configurable + Custom lists | Configurable + Custom |
| **Priority Support** | ❌ | Email | Email/Chat | Dedicated manager |
| **API Access** | ❌ | ❌ | Read-only | Full |
| **Webhooks** | ❌ | ❌ | ✅ | ✅ |
| **SSO/SAML** | ❌ | ❌ | ❌ | ✅ |
| **Storage** | 100 MB | 1 GB | 5 GB | 50 GB |
| **API Calls/Hour** | 100 | 1,000 | 10,000 | 100,000 |

---

## Quota Types & Reset Frequency

### PARTICIPANTS (Per Event)

- **Scope:** Simultaneous participants in one quiz session
- **Reset:** Per event (when session ends)
- **Check:** Before join
- **Consume:** On successful participant join
- **Release:** On participant leave

| Tier | Limit |
|------|-------|
| FREE | 50 |
| BASIC | 100 |
| PRO | 1,000 |
| ENTERPRISE | Unlimited (-1) |

### QUESTIONS (Per Quiz)

- **Scope:** Total questions per quiz definition
- **Reset:** Per quiz (new quiz = reset)
- **Check:** Before add question
- **Consume:** On add question

| Tier | Limit |
|------|-------|
| FREE | 10 |
| BASIC | 25 |
| PRO | 100 |
| ENTERPRISE | Unlimited (-1) |

### EVENTS (Concurrent)

- **Scope:** Active (CREATED or ACTIVE) quiz sessions per tenant
- **Reset:** Rolling (counted until session ends)
- **Check:** Before start quiz
- **Consume:** On start quiz

| Tier | Limit |
|------|-------|
| FREE | 1 |
| BASIC | 3 |
| PRO | 10 |
| ENTERPRISE | Unlimited (-1) |

### STORAGE (Per Tenant)

- **Scope:** Total database storage used by tenant
- **Reset:** Monthly
- **Check:** Before create large objects
- **Consume:** Automatic based on data size

| Tier | Limit |
|------|-------|
| FREE | 100 MB |
| BASIC | 1 GB |
| PRO | 5 GB |
| ENTERPRISE | 50 GB |

### API_CALLS (Per Tenant)

- **Scope:** API requests per hour
- **Reset:** Hourly (rolling window)
- **Check:** Before process API request
- **Consume:** After request processing

| Tier | Limit |
|------|-------|
| FREE | 100/hour |
| BASIC | 1,000/hour |
| PRO | 10,000/hour |
| ENTERPRISE | 100,000/hour |

### EXPORTS (Per Tenant)

- **Scope:** Data export operations per day
- **Reset:** Daily (UTC 00:00)
- **Check:** Before export operation
- **Consume:** On successful export

| Tier | Limit |
|------|-------|
| FREE | 0/day (disabled) |
| BASIC | 10/day |
| PRO | 50/day |
| ENTERPRISE | Unlimited (-1) |

---

## Feature Gate Definitions

### quiz_types

Enabled question types for this tier.

```json
{
  "FREE": ["mcq"],
  "BASIC": ["mcq", "poll"],
  "PRO": ["mcq", "poll", "word_cloud", "survey"],
  "ENTERPRISE": ["mcq", "poll", "word_cloud", "survey", "custom"]
}
```

**How to check:**
```python
tier_config = tier_service.get_tier_config("PRO")
if "word_cloud" in tier_config.features["quiz_types"]:
    # Word cloud available
```

### custom_branding

Whether tenant can customize platform branding.

```json
{
  "FREE": false,
  "BASIC": false,
  "PRO": true,
  "ENTERPRISE": true
}
```

### branding_removal

Whether tenant can remove Swaya.me branding.

```json
{
  "FREE": false,
  "BASIC": false,
  "PRO": true,
  "ENTERPRISE": true
}
```

### data_export

Whether tenant can export quiz results.

```json
{
  "FREE": false,
  "BASIC": true,
  "PRO": true,
  "ENTERPRISE": true
}
```

### moderation_queue

Whether tenant can set up moderation for user-generated content.

```json
{
  "FREE": false,
  "BASIC": false,
  "PRO": true,
  "ENTERPRISE": true
}
```

### api_access

API access level for tenant.

```json
{
  "FREE": "none",
  "BASIC": "none",
  "PRO": "readonly",
  "ENTERPRISE": "full"
}
```

### webhook_enabled

Whether webhooks are available.

```json
{
  "FREE": false,
  "BASIC": false,
  "PRO": true,
  "ENTERPRISE": true
}
```

### sso_enabled

Whether Single Sign-On is available.

```json
{
  "FREE": false,
  "BASIC": false,
  "PRO": false,
  "ENTERPRISE": true
}
```

### profanity_mode

How to handle profane content.

```json
{
  "FREE": "reject",           // Reject submission if profanity detected
  "BASIC": "configurable",    // Admin can choose: reject/mask/moderate
  "PRO": "configurable",
  "ENTERPRISE": "configurable"
}
```

---

## Database Seed Data (tier_configs)

```sql
INSERT INTO tier_configs (tier_id, name, limits, features, is_active) VALUES

-- FREE TIER
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
  ),
  TRUE
),

-- BASIC TIER
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
  ),
  TRUE
),

-- PRO TIER
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
  ),
  TRUE
),

-- ENTERPRISE TIER
(
  'ENTERPRISE',
  'Enterprise',
  JSON_OBJECT(
    'max_participants_per_event', -1,
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
  ),
  TRUE
);
```

---

## Enforcement Points & Actions

### Join Event (Participant Join)

| Tier | Participants | Action | Upgrade CTA |
|------|-------------|--------|-------------|
| FREE | Limit: 50 | Show "Event full" error | "Upgrade to Basic for 100 participants" |
| BASIC | Limit: 100 | Show "Event full" error | "Upgrade to Pro for 1,000 participants" |
| PRO | Limit: 1,000 | Show "Event full" error | "Upgrade to Enterprise for unlimited" |

**API Response:**
```json
{
  "error": "quota_exceeded",
  "message": "This event has reached its participant limit (50)",
  "details": {
    "quota_type": "participants_per_event",
    "limit": 50,
    "consumed": 50,
    "upgrade_url": "/upgrade?tier=basic"
  }
}
```

### Add Question

| Tier | Questions | Action | Upgrade CTA |
|------|-----------|--------|-------------|
| FREE | Limit: 10 | Disable "Add Question" button | "Upgrade to Basic for 25 questions" |
| BASIC | Limit: 25 | Disable "Add Question" button | "Upgrade to Pro for 100 questions" |
| PRO | Limit: 100 | Disable "Add Question" button | "Upgrade to Enterprise for unlimited" |

**API Response:**
```json
{
  "error": "quota_exceeded",
  "message": "Question limit reached (10/10)",
  "details": {
    "quota_type": "questions_per_quiz",
    "limit": 10,
    "consumed": 10,
    "upgrade_url": "/upgrade?tier=basic&feature=questions"
  }
}
```

### Start Quiz (Concurrent Events)

| Tier | Events | Action | Upgrade CTA |
|------|--------|--------|-------------|
| FREE | Limit: 1 | Show "Only 1 concurrent event allowed" | "Upgrade to Basic for 3 events" |
| BASIC | Limit: 3 | Show "Concurrent event limit reached" | "Upgrade to Pro for 10 events" |
| PRO | Limit: 10 | Show "Concurrent event limit reached" | "Upgrade to Enterprise for unlimited" |

### Export Data

| Tier | Feature | Action | Upgrade CTA |
|------|---------|--------|-------------|
| FREE | Disabled | Hide export button | "Upgrade to Basic to export results" |
| BASIC | Enabled | Show quota (10/day) | "Upgrade to Pro for 50/day" |
| PRO | Enabled | Show quota (50/day) | "Upgrade to Enterprise for unlimited" |

---

## Upgrade Paths

### Free → Basic
- **Benefit:** 2x participants, 2.5x questions, team collaboration
- **CTA:** "Ready to collaborate? Upgrade to Basic"
- **Price:** $10-15/month

### Basic → Pro
- **Benefit:** 10x participants, 4x questions, advanced features, custom branding
- **CTA:** "Need advanced features? Upgrade to Pro"
- **Price:** $25-40/month

### Pro → Enterprise
- **Benefit:** Unlimited everything, SSO, dedicated support
- **CTA:** "Ready to scale? Contact sales for Enterprise"
- **Price:** Custom

---

## Configuration Management

### Loading Tier Configs at Startup

```python
# File: backend/core/tier_service.py

class TierService:
    def __init__(self, db: Session):
        self.db = db
        self._tier_cache = {}
        self._load_tier_configs()
    
    def _load_tier_configs(self):
        """Load all tier configs from database at startup"""
        tiers = self.db.query(TierConfig).filter(
            TierConfig.is_active == True
        ).all()
        
        for tier in tiers:
            self._tier_cache[tier.tier_id] = {
                "name": tier.name,
                "limits": json.loads(tier.limits),
                "features": json.loads(tier.features)
            }
        
        logger.info(f"Loaded {len(self._tier_cache)} tier configurations")
```

### Updating Tier Configs (Post-MVP)

```sql
-- Admin API to update limits
UPDATE tier_configs
SET limits = JSON_SET(
  limits,
  '$.max_participants_per_event', 2000
)
WHERE tier_id = 'PRO';

-- Call TierService.reload_tier_configs() to cache new values
```

---

## Monitoring & Observability

### Key Metrics

| Metric | Calculation | Purpose | Alert |
|--------|-------------|---------|-------|
| Quota Utilization | consumed/limit | Identify upgrade candidates | >80% |
| Tier Distribution | COUNT(*) per tier | Revenue planning | N/A |
| Tier Restriction Rate | (rejections/requests) | Feature discoverability | >10% |
| Quota Exceeded Rate | (quota_errors/requests) | Capacity planning | >5% |
| Upgrade Conversion | (upgrades/restrictions) | Product optimization | <2% |

### Sample Query

```sql
-- Quota utilization by tier
SELECT 
  t.subscription_tier,
  q.quota_type,
  COUNT(*) as num_tenants,
  AVG(q.consumed / q.quota_limit * 100) as avg_utilization
FROM tenants t
JOIN usage_quotas q ON t.tenant_id = q.tenant_id
GROUP BY t.subscription_tier, q.quota_type;
```

---

## Version Control

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-30 | Initial tier structure (MVP) |
| 1.1 | TBD | Post-MVP: Add Word Cloud, Survey types |
| 1.2 | TBD | Post-MVP: API tier updates |
| 2.0 | TBD | V1: Custom tier definitions |

---

## Implementation Checklist

- [ ] tier_configs table created
- [ ] Seed data inserted (FREE, BASIC, PRO, ENTERPRISE)
- [ ] TierService loads configs at startup
- [ ] Feature gates implemented in UI
- [ ] Quota enforcement at API endpoints
- [ ] Upgrade CTAs added to error responses
- [ ] Admin API for tier management (post-MVP)
- [ ] Monitoring dashboards created
- [ ] Tier pricing published on website
- [ ] Billing integration ready (post-MVP)
