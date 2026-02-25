# Multi-Tenant Admin Role Assignment - Problem & Solutions

**Document Version:** 1.0  
**Date:** February 24, 2026  
**Status:** Proposal for Discussion  
**Impact:** Critical - Affects all new organization registrations

---

## Executive Summary

**Problem:** The current registration flow creates new organizations (tenants) with the first user assigned as "user" role instead of "admin" role, resulting in organizations with no administrative capability.

**Impact:** Organizations cannot manage themselves - no ability to create users, manage quizzes, or perform administrative functions.

**Recommended Solution:** Automatically assign "admin" role to the first user who creates a tenant during registration.

**Complexity:** Low (1-line code change + migration script)  
**Risk:** Low (backwards compatible with migration)  
**Urgency:** High (affects every new organization)

---

## Problem Statement

### Current Registration Flow

```
User Registers → Creates New Tenant → Assigned "user" Role → ❌ Cannot Manage Organization
```

### What Happens Now

1. User visits registration page
2. Fills in:
   - Tenant Name (e.g., "Saint John's Academy")
   - Email
   - Full Name
   - Password
3. System creates:
   - **NEW tenant** with provided name
   - **NEW user** with `role = "user"` (default)
4. User logs in → Has NO administrative privileges

### Real-World Impact

**Example: Saint John's Academy (Current Production Issue)**

| User | Email | Role | Can Create Users? | Can Manage Org? |
|------|-------|------|-------------------|-----------------|
| Student | 5012@saintjohnsacademy.com | user | ❌ No | ❌ No |
| Student | 5588@saintjohnsacademy.com | user | ❌ No | ❌ No |
| Faculty | (not yet registered) | would be "user" | ❌ No | ❌ No |

**Result:** Saint John's Academy has an organization account but no one can manage it!

### Why This is a Universal Problem

This affects **any** type of organization:

- **Educational Institutions:** Students register before faculty
- **Startups:** Anyone can register, even non-founders
- **Clubs/Teams:** Members register before leaders
- **Businesses:** Employees register before managers

**The fundamental issue:** The person who **creates** the organization isn't automatically its **admin**.

---

## Root Cause Analysis

### Code Location

**File:** `backend/core/auth/service.py`  
**Function:** `register_user()`  
**Lines:** 67-75

```python
user = User(
    tenant_id=tenant.id,
    email=request.email,
    hashed_password=hash_password(request.password),
    full_name=request.full_name,
    is_active=True,
    # role defaults to UserRole.USER from model ← PROBLEM!
    login_count=1,
    last_login_at=datetime.now(timezone.utc)
)
```

### Model Default

**File:** `backend/persistence/models/core.py`  
**Line:** 59

```python
class User(Base, TimestampMixin):
    # ...
    role = Column(SQLEnum(UserRole), nullable=False, 
                  default=UserRole.user,           # ← Default is "user"
                  server_default="user")
```

### Why It Happens

- Registration creates a **new tenant** (organization)
- User is created with **default role** from model
- Default role is `UserRole.USER`
- No explicit role assignment during registration
- User has no admin privileges for the org they created

---

## Solution Options

### Option 1: First Registrant = Admin (RECOMMENDED)

**Concept:** The person who creates an organization automatically becomes its admin.

#### Implementation

**Single-line fix in registration service:**

```python
# File: backend/core/auth/service.py
# Function: register_user()

user = User(
    tenant_id=tenant.id,
    email=request.email,
    hashed_password=hash_password(request.password),
    full_name=request.full_name,
    is_active=True,
    role=UserRole.ADMIN,  # ← ADD THIS LINE
    login_count=1,
    last_login_at=datetime.now(timezone.utc)
)
```

#### Pros

- ✅ **Intuitive:** Creator owns organization (natural expectation)
- ✅ **Simple:** One-line code change
- ✅ **Universal:** Works for all organization types
- ✅ **Self-service:** No manual intervention needed
- ✅ **Scalable:** Works for 1 user or 10,000 organizations
- ✅ **Minimal Risk:** Small, isolated change
- ✅ **Fast:** 15-minute development + testing

#### Cons

- ⚠️ **Existing Data:** Current users need migration
- ⚠️ **Edge Case:** What if wrong person registers first? (Rare, solvable)

#### Migration Required

```python
# One-time migration script
for tenant in all_tenants:
    users = get_users_ordered_by_created_at(tenant.id)
    if users and users[0].role == UserRole.USER:
        users[0].role = UserRole.ADMIN
        db.commit()
```

---

### Option 2: Organization Invite Codes

**Concept:** Each organization has invite codes. Code type determines role.

#### How It Works

1. First user registers → Creates tenant → Gets "admin" + invite codes
2. Admin generates codes:
   - Admin Code: `ORG-ADMIN-XYZ123`
   - User Code: `ORG-USER-ABC456`
3. Others join using invite code → Role assigned based on code type

#### Registration Flow Change

```
Current:                     Proposed:
┌─────────────────┐         ┌──────────────────────┐
│ Tenant Name     │         │ Invite Code          │ ← NEW
│ Email           │         │ (or create new org)  │
│ Password        │         │ Email                │
└─────────────────┘         │ Password             │
                            └──────────────────────┘
```

#### Pros

- ✅ **Control:** Admins decide who gets admin role
- ✅ **Prevents Duplicates:** Can't create duplicate tenants
- ✅ **Role Assignment:** Automatic based on invite type
- ✅ **Audit Trail:** Track who invited whom

#### Cons

- ❌ **Complex:** Significant development work (2-3 days)
- ❌ **UX Change:** Registration flow becomes more complex
- ❌ **Migration:** Harder to implement for existing users
- ❌ **Code Sharing:** Users need to share codes externally
- ❌ **Discovery:** How do users find the right invite code?

#### Implementation Estimate

- Database: New `invite_codes` table
- Backend: Code generation, validation, expiry logic
- Frontend: Modified registration form, code management UI
- Testing: Complex user flows
- **Total:** 2-3 days development

---

### Option 3: Role Change Request System

**Concept:** Users can request admin role. Super admin approves.

#### How It Works

```
User Dashboard:
┌────────────────────────────────────┐
│ Current Role: User                 │
│ Need administrative access?        │
│ [Request Admin Role] button        │
└────────────────────────────────────┘
         ↓
Super Admin Notification:
┌────────────────────────────────────┐
│ Role Change Request                │
│ User: john@acme.com                │
│ Org: Acme Corp                     │
│ Requested: Admin                   │
│ [Approve] [Deny]                   │
└────────────────────────────────────┘
```

#### Pros

- ✅ **Self-service:** Users can request
- ✅ **Controlled:** Super admin approves
- ✅ **Audit Trail:** Track all requests

#### Cons

- ❌ **Manual:** Still requires super admin intervention
- ❌ **Delay:** Not instant - users must wait
- ❌ **Complex:** Development work required (1-2 days)
- ❌ **Notification System:** Email/push notifications needed
- ❌ **Doesn't Scale:** Super admin becomes bottleneck

---

### Option 4: Email Domain-Based Auto-Role

**Concept:** Assign roles based on email domain patterns.

#### Example Configuration

```python
DOMAIN_ROLE_MAPPING = {
    '@faculty.sja.com': 'admin',
    '@sja.com': 'user',
    '@admin.acme.com': 'admin',
    '@acme.com': 'user'
}
```

#### Pros

- ✅ **Automatic:** No manual steps
- ✅ **Simple:** Easy to implement

#### Cons

- ❌ **Inflexible:** Requires email domain conventions
- ❌ **Configuration:** Needs per-tenant setup
- ❌ **Personal Emails:** Doesn't work with gmail.com, etc.
- ❌ **Maintenance:** Must update mappings
- ❌ **Edge Cases:** What about contractors, partners?

---

### Option 5: Manual Promotion (Status Quo)

**Concept:** Super admin manually promotes users to admin via User Management.

#### Current Workaround

1. User registers with "user" role
2. Contacts super admin
3. Super admin edits user → Changes role to "admin"
4. User can now manage organization

#### Pros

- ✅ **No Development:** Already implemented
- ✅ **Complete Control:** Super admin decides

#### Cons

- ❌ **Not Scalable:** Manual work for every organization
- ❌ **Poor UX:** Users get stuck, frustrated
- ❌ **Support Burden:** Constant requests for promotion
- ❌ **Delays:** Users can't use system until promoted
- ❌ **Discovery:** Users might not know to ask

---

## Comparison Matrix

| Solution | Complexity | Dev Time | User Experience | Scalability | Maintenance | Recommended |
|----------|-----------|----------|-----------------|-------------|-------------|-------------|
| **First = Admin** | ⭐ Low | 15 min | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ None | ✅ **YES** |
| Invite Codes | ⭐⭐⭐ High | 2-3 days | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Good | ⭐⭐⭐ Medium | ⚠️ Future |
| Role Requests | ⭐⭐ Medium | 1-2 days | ⭐⭐ Fair | ⭐⭐ Poor | ⭐⭐⭐ Medium | ❌ No |
| Email Domain | ⭐⭐ Medium | 1 day | ⭐⭐ Fair | ⭐⭐ Poor | ⭐⭐ High | ❌ No |
| Manual Promotion | ⭐ Low | 0 | ⭐ Poor | ⭐ Very Poor | ⭐ Very High | ❌ No |

---

## Recommended Implementation Plan

### Phase 1: Immediate Fix (Week 1)

**Goal:** Fix the core issue for all future registrations

**Tasks:**
1. Update registration service to assign `role=UserRole.ADMIN`
2. Write migration script for existing tenants
3. Test registration flow
4. Deploy to production
5. Run migration on existing data

**Impact:** All new organizations will have proper admin access immediately

**Effort:** 2-4 hours (including testing)

### Phase 2: Enhanced Controls (Future - Optional)

**Goal:** Add more sophisticated role management

**Possible Enhancements:**
- Invite code system (if org control needed)
- Multiple admin support (already works)
- Role delegation features
- Self-service role requests

**Timeline:** After Phase 1 is stable and if needed based on usage patterns

---

## Migration Strategy

### For Existing Tenants

**Option A: Promote First User (Recommended)**

```sql
-- SQL Migration (safer than script)
UPDATE users u1
INNER JOIN (
    SELECT tenant_id, MIN(id) as first_user_id
    FROM users
    GROUP BY tenant_id
) u2 ON u1.id = u2.first_user_id
SET u1.role = 'admin'
WHERE u1.role = 'user';
```

**Option B: Manual Review**

For sensitive cases (like SJA with student first):
1. Review each tenant
2. Identify correct admin (faculty, not student)
3. Manually promote via User Management
4. Document decisions

### Rollback Plan

If issues occur:
```sql
-- Restore original roles (within 24 hours)
UPDATE users
SET role = 'user'
WHERE updated_at > '[migration_timestamp]'
AND role = 'admin';
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Wrong person becomes admin | Low | Medium | Super admin can change roles |
| Breaks existing functionality | Very Low | High | Small, isolated change + testing |
| Data migration issues | Low | Medium | Test on staging first, SQL backup |
| User confusion | Very Low | Low | No UI changes, intuitive behavior |

**Overall Risk Level:** ⚠️ LOW

---

## Success Metrics

### Short-term (Week 1)

- ✅ 100% of new registrations get admin role
- ✅ Zero support tickets about "can't create users"
- ✅ Existing tenants migrated successfully
- ✅ No regression in registration flow

### Long-term (Month 1)

- 📈 Reduced super admin interventions by 95%
- 📈 Faster organization setup (self-service)
- 📈 Improved user satisfaction scores
- 📈 No duplicate tenant creations

---

## Technical Specifications

### Code Changes Required

**File 1:** `backend/core/auth/service.py`
```python
# Line ~67, in register_user() function
user = User(
    tenant_id=tenant.id,
    email=request.email,
    hashed_password=hash_password(request.password),
    full_name=request.full_name,
    is_active=True,
    role=UserRole.ADMIN,  # ← CHANGE: was defaulting to USER
    login_count=1,
    last_login_at=datetime.now(timezone.utc)
)
```

**File 2:** Migration script (new file)
```python
# backend/scripts/migrate_first_users_to_admin.py
"""Promote first user of each tenant to admin role"""

def migrate_first_users():
    tenants = db.query(Tenant).all()
    for tenant in tenants:
        users = db.query(User).filter(
            User.tenant_id == tenant.id
        ).order_by(User.created_at.asc()).all()
        
        if users and users[0].role == UserRole.USER:
            users[0].role = UserRole.ADMIN
            db.commit()
            print(f"Promoted {users[0].email} to admin for {tenant.name}")
```

### Testing Checklist

- [ ] Unit test: User creation sets admin role
- [ ] Integration test: Full registration flow
- [ ] E2E test: Register → Login → Create user (should work)
- [ ] Migration test: Run on staging database
- [ ] Rollback test: Verify rollback script works
- [ ] Production test: Monitor first 10 registrations

---

## Alternatives Considered and Rejected

### Two-Step Registration

**Idea:** Ask "Are you creating an organization or joining one?" first

**Rejected because:**
- Adds complexity to UX
- Doesn't solve role assignment
- Still needs invite codes (Option 2)

### Approval-Based Registration

**Idea:** Super admin approves all new tenants

**Rejected because:**
- Terrible UX (users must wait)
- Not scalable
- Discourages adoption

### Tenant Templates

**Idea:** Pre-configured tenant types (school, business, etc.) with different defaults

**Rejected because:**
- Over-engineered
- Still doesn't solve core issue
- Adds unnecessary complexity

---

## Discussion Questions

1. **Scope:** Do we implement Phase 1 only, or also plan Phase 2?
2. **Migration:** Promote all first users automatically, or manual review for each tenant?
3. **Timeline:** Can we deploy this in the next sprint?
4. **Documentation:** What user-facing docs need updating?
5. **Communication:** How do we notify existing users about role changes?
6. **Edge Cases:** How do we handle the SJA situation (students vs faculty)?

---

## Recommendation

**Implement Option 1: First Registrant = Admin**

**Rationale:**
- ✅ Solves 95% of use cases perfectly
- ✅ Minimal development effort (15 minutes)
- ✅ Low risk (isolated change)
- ✅ Intuitive user experience
- ✅ Self-service (no support burden)
- ✅ Can add invite codes later if needed

**Next Steps:**
1. Team reviews this document
2. Approval to proceed
3. Implement change (2-4 hours)
4. Deploy to staging
5. Test thoroughly
6. Deploy to production
7. Run migration
8. Monitor for 1 week

---

## Appendix: Current Production Data

### Affected Tenants

| Tenant ID | Name | First User | Role | Created | Issue |
|-----------|------|-----------|------|---------|-------|
| 2 | Demo Organization | demo@swaya.me | super_admin | Feb 12 | ✅ OK (has admin) |
| 3 | AG | ami.gillon@yale.edu | user | Feb 20 | ❌ No admin |
| 4 | SJA | 5012@saintjohnsacademy.com | user | Feb 24 | ❌ No admin (student) |
| 5 | SJA | 5588@saintjohnsacademy.com | user | Feb 24 | ❌ Duplicate tenant |

**Total Affected:** 3 out of 4 tenants (75%)

---

## References

- Architecture Doc: `Docs/multi-tenant-migration.md`
- Code: `backend/core/auth/service.py`
- Model: `backend/persistence/models/core.py`
- User Management: `frontend/src/features/admin/components/UserManagement.jsx`

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-24 | System | Initial document for team discussion |

---

**Status:** Ready for team discussion  
**Priority:** High  
**Complexity:** Low  
**Impact:** Critical
