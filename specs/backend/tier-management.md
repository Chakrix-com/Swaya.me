# Tier Management & Entitlements (Backend Implementation)

## Overview

This document defines the backend implementation strategy for subscription tier management, feature gates, and quota enforcement in Swaya.me.

**Technology Commitment:** 100% open source (FastAPI, SQLAlchemy, Redis, all MIT/Apache 2.0/BSD licensed).

---

## Architecture: Tier Enforcement in 3 Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Services Layer (API/Realtime)                               │
│ - Translates client intent into platform commands           │
│ - NO tier logic, NO quota checks                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Broker Layer (Policy Enforcement) *** TIER GATES HERE ***   │
│ - Middleware: Resolve tenant context (once per request)     │
│ - Policy Enforcement: Check feature gates                   │
│ - Quota Enforcement: Check limits before routing            │
│ - Auth + Rate Limit + Profanity + Tier Checks               │
│ - Route to feature or reject with upgrade CTA               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Platform Kernel (Orchestration)                             │
│ - Invokes features with tenant context                      │
│ - Features are tier-agnostic                                │
│ - Consumes quotas AFTER feature execution                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Features Layer (Quiz, Polls, etc.)                          │
│ - NO tier awareness                                         │
│ - NO quota tracking                                         │
│ - NO tenant resolution                                      │
│ - Tenant context provided by Platform                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Services (Layer 1: Identity & Tier Management)

### TenantService

**Responsibility:** Manages tenant registration, context, and configuration.

```python
# File: backend/core/tenant_service.py

class TenantService:
    """
    Manages multi-tenant context across the platform.
    Resolves and caches tenant information once per request.
    """
    
    def __init__(self, db_session: Session, cache: Redis):
        self.db = db_session
        self.cache = cache
    
    async def get_tenant_by_id(self, tenant_id: UUID) -> Tenant:
        """
        Retrieve tenant by ID with caching.
        
        Cache TTL: 5 minutes (tier changes are infrequent)
        Fallback: Database query if cache miss
        """
        cache_key = f"tenant:{tenant_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return Tenant.parse_obj(cached)
        
        tenant = self.db.query(Tenant).filter(
            Tenant.tenant_id == tenant_id
        ).first()
        
        if not tenant:
            raise TenantNotFoundError(tenant_id)
        
        self.cache.setex(cache_key, 300, tenant.dict())
        return tenant
    
    async def get_tenant_by_slug(self, slug: str) -> Tenant:
        """Retrieve tenant by slug (URL-safe identifier)"""
        pass
    
    async def create_tenant(
        self, 
        name: str, 
        slug: str, 
        subscription_tier: str = "FREE"
    ) -> Tenant:
        """
        Create new tenant (signup flow).
        
        Args:
            name: Organization name
            slug: URL-safe identifier (unique globally)
            subscription_tier: Initial tier (FREE|BASIC|PRO|ENTERPRISE)
        
        Returns:
            Created Tenant with assigned tier configuration
        """
        # Validate slug uniqueness
        if self.db.query(Tenant).filter(Tenant.slug == slug).first():
            raise TenantSlugAlreadyExists(slug)
        
        tenant = Tenant(
            tenant_id=uuid4(),
            name=name,
            slug=slug,
            subscription_tier=subscription_tier,
            subscription_status=SubscriptionStatus.TRIAL,
            subscription_start=datetime.utcnow()
        )
        
        self.db.add(tenant)
        self.db.commit()
        
        # Initialize usage quotas for this tenant
        await self._initialize_quotas(tenant.tenant_id)
        
        return tenant
    
    async def _initialize_quotas(self, tenant_id: UUID):
        """Initialize quota tracking for new tenant"""
        pass
    
    async def invalidate_cache(self, tenant_id: UUID):
        """Invalidate tenant cache on subscription change"""
        cache_key = f"tenant:{tenant_id}"
        self.cache.delete(cache_key)
```

### EntitlementService

**Responsibility:** Manages feature gates and quota enforcement.

```python
# File: backend/core/entitlement_service.py

class EntitlementService:
    """
    Enforces subscription tier limits and feature access.
    
    Policy: Features are gated at Broker layer BEFORE execution.
    Quotas are consumed AFTER successful feature execution.
    """
    
    def __init__(self, db_session: Session, cache: Redis, tier_service: TierService):
        self.db = db_session
        self.cache = cache
        self.tier_service = tier_service
    
    async def check_feature_access(self, tenant_id: UUID, feature: str) -> bool:
        """
        Check if tenant's tier includes a specific feature.
        
        Args:
            tenant_id: Organization ID
            feature: Feature identifier (e.g., 'custom_branding', 'data_export')
        
        Returns:
            True if feature is available for tenant's tier
        
        Raises:
            TierRestrictionError if feature not available
        """
        tenant = await self.tenant_service.get_tenant_by_id(tenant_id)
        tier_config = await self.tier_service.get_tier_config(tenant.subscription_tier)
        
        is_enabled = tier_config.features.get(feature, False)
        
        if not is_enabled:
            raise TierRestrictionError(
                feature=feature,
                current_tier=tenant.subscription_tier,
                required_tier=self._get_min_tier_for_feature(feature)
            )
        
        return True
    
    async def check_quota_available(
        self, 
        tenant_id: UUID, 
        quota_type: QuotaType, 
        amount: int = 1
    ) -> bool:
        """
        Check if tenant has quota available.
        
        Args:
            tenant_id: Organization ID
            quota_type: PARTICIPANTS|QUESTIONS|EVENTS|API_CALLS|STORAGE|EXPORTS
            amount: Amount to check (default: 1)
        
        Returns:
            True if quota available, False otherwise
        
        Usage Example:
            # Check before participant join
            if not await entitlements.check_quota_available(
                tenant_id, 
                QuotaType.PARTICIPANTS, 
                amount=1
            ):
                raise QuotaExceededError("Participant limit reached")
        """
        quota = self.db.query(UsageQuota).filter(
            UsageQuota.tenant_id == tenant_id,
            UsageQuota.quota_type == quota_type
        ).first()
        
        if not quota:
            raise QuotaNotInitializedError(tenant_id, quota_type)
        
        # Check if within period
        now = datetime.utcnow()
        if now < quota.period_start or now > quota.period_end:
            # Period expired, reset quota
            await self._reset_quota(quota)
        
        # Unlimited check (-1 means unlimited)
        if quota.limit == -1:
            return True
        
        return quota.consumed + amount <= quota.limit
    
    async def consume_quota(
        self, 
        tenant_id: UUID, 
        quota_type: QuotaType, 
        amount: int = 1
    ) -> None:
        """
        Increment quota consumption.
        
        Called AFTER successful feature execution.
        
        Usage Example:
            # After participant successfully joins session
            await entitlements.consume_quota(
                tenant_id, 
                QuotaType.PARTICIPANTS, 
                amount=1
            )
        """
        quota = self.db.query(UsageQuota).filter(
            UsageQuota.tenant_id == tenant_id,
            UsageQuota.quota_type == quota_type
        ).first()
        
        if not quota:
            raise QuotaNotInitializedError(tenant_id, quota_type)
        
        quota.consumed += amount
        quota.last_updated = datetime.utcnow()
        
        self.db.commit()
        
        # Log quota consumption for analytics
        await self._log_quota_event(tenant_id, quota_type, amount, "consumed")
    
    async def release_quota(
        self, 
        tenant_id: UUID, 
        quota_type: QuotaType, 
        amount: int = 1
    ) -> None:
        """
        Decrement quota consumption (e.g., participant leaves event).
        
        Usage Example:
            # When participant leaves session
            await entitlements.release_quota(
                tenant_id, 
                QuotaType.PARTICIPANTS, 
                amount=1
            )
        """
        quota = self.db.query(UsageQuota).filter(
            UsageQuota.tenant_id == tenant_id,
            UsageQuota.quota_type == quota_type
        ).first()
        
        if not quota:
            return
        
        quota.consumed = max(0, quota.consumed - amount)
        quota.last_updated = datetime.utcnow()
        
        self.db.commit()
    
    async def get_quota_status(self, tenant_id: UUID) -> dict:
        """
        Get current quota utilization for all quota types.
        
        Returns:
            {
                "PARTICIPANTS": {"limit": 1000, "consumed": 750, "pct": 75},
                "QUESTIONS": {"limit": 100, "consumed": 42, "pct": 42},
                ...
            }
        """
        quotas = self.db.query(UsageQuota).filter(
            UsageQuota.tenant_id == tenant_id
        ).all()
        
        return {
            quota.quota_type.value: {
                "limit": quota.limit if quota.limit != -1 else "unlimited",
                "consumed": quota.consumed,
                "pct": (quota.consumed / quota.limit * 100) if quota.limit != -1 else 0
            }
            for quota in quotas
        }
```

### TierService

**Responsibility:** Manages tier configuration caching and lookup.

```python
# File: backend/core/tier_service.py

class TierService:
    """
    Manages tier configurations and feature/limit lookups.
    
    Tier configs loaded at startup and cached in memory (rarely change).
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self._tier_cache: Dict[str, TierConfig] = {}
        self._load_tier_configs()
    
    def _load_tier_configs(self):
        """Load all active tier configurations into memory"""
        tiers = self.db.query(TierConfig).filter(
            TierConfig.is_active == True
        ).all()
        
        for tier in tiers:
            self._tier_cache[tier.tier_id] = tier
    
    def get_tier_config(self, tier_id: str) -> TierConfig:
        """
        Get tier configuration by ID (in-memory lookup).
        
        Raises:
            TierNotFoundError if tier_id invalid
        """
        if tier_id not in self._tier_cache:
            raise TierNotFoundError(tier_id)
        
        return self._tier_cache[tier_id]
    
    def get_feature_for_tier(self, tier_id: str, feature: str) -> bool:
        """Get feature enablement for a specific tier"""
        tier = self.get_tier_config(tier_id)
        return tier.features.get(feature, False)
    
    def get_limit_for_tier(self, tier_id: str, limit_name: str) -> int:
        """Get quota limit for a specific tier"""
        tier = self.get_tier_config(tier_id)
        return tier.limits.get(limit_name, 0)
    
    def reload_tier_configs(self):
        """Reload tier configs from database (call after admin updates)"""
        self._tier_cache.clear()
        self._load_tier_configs()
```

---

## Broker Layer Policy Enforcement

### TenantContextMiddleware

**Responsibility:** Extract and attach tenant context to every request (once per request).

```python
# File: backend/broker/middleware/tenant_context.py

@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next) -> Response:
    """
    Middleware to resolve tenant context once per request.
    
    Flow:
    1. Extract tenant ID from JWT/session token
    2. Load tenant config with caching
    3. Validate subscription status
    4. Attach to request.state.tenant
    5. Pass to endpoint
    
    Execution Order: FIRST (before all other middleware)
    """
    try:
        # Extract tenant ID from Authorization header or session cookie
        tenant_id = extract_tenant_from_request(request)
        
        if not tenant_id:
            raise MissingTenantContextError("No tenant context in request")
        
        # Load tenant context (cached, 5-minute TTL)
        tenant_context = await tenant_service.get_tenant_by_id(tenant_id)
        
        # Validate subscription status
        if tenant_context.subscription_status not in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIAL
        ]:
            raise SubscriptionInactiveError(
                tenant_id, 
                tenant_context.subscription_status
            )
        
        # Attach to request
        request.state.tenant = tenant_context
        request.state.tenant_id = tenant_id
        
        # Log request with tenant context
        logger.info(
            "Request received",
            extra={
                "tenant_id": tenant_id,
                "method": request.method,
                "path": request.url.path
            }
        )
        
        response = await call_next(request)
        return response
        
    except TenantError as e:
        logger.error(f"Tenant context error: {e}")
        return JSONResponse(
            status_code=403,
            content={"error": "tenant_context_error", "message": str(e)}
        )
```

### TierPolicyEnforcement

**Responsibility:** Check tier gates and quotas before routing to features.

```python
# File: backend/broker/middleware/tier_policy.py

async def enforce_tier_policies(request: Request) -> None:
    """
    Enforce tier-based policies before routing to features.
    
    Checks:
    1. Feature gate (tier includes feature?)
    2. Quota available (under limit?)
    3. Rate limits (per-IP, per-session)
    
    Execution Order: AFTER tenant_context_middleware
    
    Raises:
    - TierRestrictionError (403): Feature not in tier
    - QuotaExceededError (429): Limit reached
    - RateLimitError (429): Too many requests
    """
    tenant = request.state.tenant
    
    # Get feature key from endpoint metadata
    feature_key = get_feature_for_route(request.url.path, request.method)
    
    if not feature_key:
        # Route doesn't require tier check
        return
    
    # Check feature gate
    try:
        await entitlement_service.check_feature_access(tenant.tenant_id, feature_key)
    except TierRestrictionError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "tier_restriction",
                "message": f"Feature '{feature_key}' requires upgrade",
                "current_tier": tenant.subscription_tier,
                "required_tier": e.required_tier,
                "upgrade_url": f"/upgrade?target={feature_key}"
            }
        )
    
    # Check quota (if applicable)
    quota_type = get_quota_type_for_feature(feature_key)
    if quota_type:
        if not await entitlement_service.check_quota_available(
            tenant.tenant_id, 
            quota_type
        ):
            quota_status = await entitlement_service.get_quota_status(tenant.tenant_id)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "quota_exceeded",
                    "message": f"Quota limit reached for {quota_type}",
                    "quota_type": quota_type,
                    "limit": quota_status[quota_type]["limit"],
                    "consumed": quota_status[quota_type]["consumed"],
                    "upgrade_url": "/upgrade"
                }
            )


# Attach to app with correct execution order
app.add_middleware(TierPolicyEnforcement)
```

---

## Quota Consumption Pattern

### Key Principle: Check BEFORE, Consume AFTER

```
Request arrives
    ↓
[Tenant Context Middleware] ← Resolve tenant once
    ↓
[Tier Policy Enforcement] ← Check feature gate + quota
    ↓
[Feature Execution] ← Feature has no tier awareness
    ↓
[Quota Consumption] ← Consume quota AFTER success
    ↓
Response sent
```

### Example: Participant Join

```python
# File: backend/broker/routes/quiz.py

@router.post("/quiz/{session_id}/join")
async def join_quiz(
    session_id: UUID,
    request: Request,
    display_name: str = Query(...)
):
    """
    Join a quiz session.
    
    Step 1: Middleware checked tenant context ✓
    Step 2: Middleware checked PARTICIPANTS quota ✓
    Step 3: Platform invokes Quiz feature
    Step 4: Quiz validates and creates participant
    Step 5: Consume quota
    """
    tenant_id = request.state.tenant_id
    
    try:
        # Platform layer calls feature
        participant = await quiz_feature.add_participant(
            session_id=session_id,
            display_name=display_name,
            tenant_id=tenant_id
        )
        
        # Quota consumed AFTER successful join
        await entitlement_service.consume_quota(
            tenant_id,
            QuotaType.PARTICIPANTS,
            amount=1
        )
        
        return {"participant_id": participant.id, "status": "joined"}
        
    except QuizSessionFullError:
        # Don't consume quota on failure
        raise HTTPException(
            status_code=409,
            detail="Session is full. Upgrade to increase limit."
        )
```

### Example: Quiz Creation

```python
@router.post("/quiz")
async def create_quiz(
    request: Request,
    payload: CreateQuizPayload
):
    """Create new quiz"""
    tenant_id = request.state.tenant_id
    
    try:
        quiz = await quiz_feature.create_quiz(
            title=payload.title,
            description=payload.description,
            tenant_id=tenant_id,
            host_id=request.state.user_id
        )
        
        # Quota consumed after creation
        await entitlement_service.consume_quota(
            tenant_id,
            QuotaType.QUESTIONS,  # Reserve for this quiz
            amount=0  # Consumed per question added, not per quiz
        )
        
        return {"quiz_id": quiz.id, "status": "created"}
        
    except Exception as e:
        # Fail gracefully
        raise HTTPException(status_code=400, detail=str(e))
```

---

## Tier Configuration Structure

### Tier Limits (Database JSON)

```json
{
  "free": {
    "limits": {
      "max_participants_per_event": 50,
      "max_questions_per_quiz": 10,
      "max_concurrent_events": 1,
      "max_team_members": 1,
      "event_history_days": 7,
      "storage_mb": 100,
      "api_calls_per_hour": 100,
      "exports_per_day": 0
    },
    "features": {
      "quiz_types": ["mcq"],
      "custom_branding": false,
      "data_export": false,
      "profanity_mode": "reject"
    }
  },
  "pro": {
    "limits": {
      "max_participants_per_event": 1000,
      "max_questions_per_quiz": 100,
      "max_concurrent_events": 10,
      "max_team_members": 10,
      "event_history_days": 365,
      "storage_mb": 5000,
      "api_calls_per_hour": 10000,
      "exports_per_day": 50
    },
    "features": {
      "quiz_types": ["mcq", "poll", "word_cloud"],
      "custom_branding": true,
      "data_export": true,
      "api_access": "readonly",
      "profanity_mode": "configurable"
    }
  }
}
```

---

## Error Responses

### TierRestrictionError (403)

```json
{
  "error": "tier_restriction",
  "message": "This feature requires a Professional plan",
  "details": {
    "feature": "custom_branding",
    "current_tier": "free",
    "required_tier": "pro",
    "upgrade_url": "/upgrade?target=custom_branding"
  }
}
```

### QuotaExceededError (429)

```json
{
  "error": "quota_exceeded",
  "message": "Participant limit reached for this event",
  "details": {
    "quota_type": "participants_per_event",
    "limit": 50,
    "consumed": 50,
    "reset_at": "2026-02-01T00:00:00Z",
    "upgrade_url": "/upgrade"
  }
}
```

---

## Testing Strategy

### Unit Tests (Feature Layer)

```python
# features/quiz/test_quota_validation.py

async def test_question_limit_enforced():
    """Ensure question count limit is validated"""
    tenant = create_test_tenant(tier="FREE")
    quiz = create_test_quiz(tenant_id=tenant.id)
    
    # Add 10 questions (free tier limit)
    for i in range(10):
        await quiz_feature.add_question(quiz.id, f"Q{i}")
    
    # Should reject 11th question
    with pytest.raises(QuestionLimitExceededError):
        await quiz_feature.add_question(quiz.id, "Q11")
```

### Integration Tests (Broker Layer)

```python
# broker/test_tier_enforcement.py

async def test_free_tier_export_rejected():
    """Free tier cannot export data"""
    client = create_client(tier="FREE")
    
    response = await client.post("/api/quiz/export", json={
        "quiz_id": "123",
        "format": "csv"
    })
    
    assert response.status_code == 403
    assert response.json()["error"] == "tier_restriction"
```

### E2E Tests

```python
# e2e/test_upgrade_flow.py

async def test_upgrade_from_free_to_pro():
    """User upgrades tier and gains access to features"""
    tenant = create_test_tenant(tier="FREE")
    
    # Attempt export with FREE tier
    response = await client.post("/api/quiz/export")
    assert response.status_code == 403
    
    # Upgrade to PRO
    await tenant_service.update_subscription_tier(
        tenant.id, 
        tier="PRO"
    )
    
    # Export now succeeds
    response = await client.post("/api/quiz/export")
    assert response.status_code == 200
```

---

## Implementation Checklist

- [ ] Database tables created (tenants, tier_configs, usage_quotas)
- [ ] TenantService implemented
- [ ] EntitlementService implemented
- [ ] TierService implemented
- [ ] TenantContextMiddleware deployed
- [ ] TierPolicyEnforcement middleware deployed
- [ ] Quota consumption logic in feature endpoints
- [ ] Error responses formatted
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Admin API for tier management (post-MVP)
- [ ] Usage dashboards (post-MVP)
