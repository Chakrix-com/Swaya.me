# Swaya.me Failure Prevention Guide

## Overview
This guide documents known failure points and how to prevent them from occurring in production.

---

## 1. Login Failures

### Current Safeguards ✅
```python
# backend/core/auth/service.py - login_user()
1. User lookup by email
2. Password verification
3. User active status check
4. Tenant existence check
5. Tenant active status check
```

### Failure Scenarios

| Scenario | Cause | Solution |
|----------|-------|----------|
| Invalid credentials | Wrong password or email doesn't exist | User sees: "Invalid email or password" ✅ |
| Account disabled | `user.is_active = False` | Explicitly checks: `if not user.is_active` ✅ |
| Tenant deleted | Tenant FK exists but `is_active = False` | Checks: `if not tenant or not tenant.is_active` ✅ |
| Inactive subscription | Tenant exists but subscription lapsed | **NOT CHECKED** ⚠️ |
| Corrupted password hash | Hash doesn't verify correctly | Re-seed with `scripts/seed_data.py` ✅ |

### Preventive Measures
- **Daily**: Monitor failed login attempts in logs
- **Weekly**: Check for inactive tenants using: `SELECT * FROM tenants WHERE is_active = FALSE;`
- **Monthly**: Audit user active status in each tenant
- **On deployment**: Always re-run `python scripts/seed_data.py` to ensure demo user is functional

---

## 2. Quiz Creation Failures

### Root Cause Analysis (Quiz - Event Mismatch)
**Problem:** Created when
- Backend: Quiz requires non-null `event_id` foreign key
- Cluster: No auto-creation of events for new quizzes
- Frontend: Hardcoded `event_id: 1` which didn't exist

**Solution Applied** ✅
- Made `event_id` optional in QuizCreate schema
- Auto-create events when `event_id` is null
- Frontend no longer passes `event_id` explicitly

### Current Safeguards ✅
```python
# backend/features/quiz/quiz_service.py - create_quiz()

# Option 1: No event_id provided → auto-create
if not request.event_id:
    event = Event(
        tenant_id=current_user.tenant_id,
        creator_id=current_user.user_id,
        title=f"Quiz Session - {request.title}",
        description=None
    )
    db.add(event)
    db.flush()
    event_id = event.id

# Option 2: event_id provided → validate
else:
    event = db.query(Event).filter(
        Event.id == request.event_id,
        Event.tenant_id == current_user.tenant_id
    ).first()
    if not event:
        raise QuizNotFoundError("Event not found")
```

---

## 3. Session Join Failures

### Failure Points

| Endpoint | Error | Cause | Prevention |
|----------|-------|-------|-----------|
| Join quiz | "Invalid join code" | Host hasn't started session yet | Clear message ✅ |
| Join quiz | "No active session found" | Session ended or doesn't exist | Clear message ✅ |
| Join quiz | "Tenant not found" | Orphaned session (shouldn't happen) | DB integrity check needed |
| Join quiz | "Participant limit reached" | Tier limit exceeded | Clear message ✅ |

### Preventive Measure
Add database integrity check:
```sql
-- Verify all sessions have valid tenants
SELECT COUNT(*) FROM quiz_sessions qs 
WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = qs.tenant_id);
-- Result should be: 0
```

---

## 4. Answer Submission Failures

### Failure Points

| Error | Cause | Prevention |
|-------|-------|-----------|
| "Invalid session token" | Participant not found | Clear error ✅ |
| "Question not open for answers" | Question status != OPEN | State machine enforces ✅ |
| "No active question" | Index out of bounds | Boundary check ✅ |
| "Question is not currently active" | Stale client state | Question ID mismatch check ✅ |
| "Already answered" | Duplicate submission attempt | Unique constraint + check ✅ |

---

## 5. Future Failure Prevention Checklist

### Before Each Production Deployment

- [ ] **Database Health**
  ```bash
  # Check foreign key integrity
  mysql swayame -u user -p -e "
  SELECT 'Users with invalid tenant' FROM users u 
  WHERE NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = u.tenant_id);
  
  SELECT 'Quizzes with invalid event' FROM quizzes q 
  WHERE NOT EXISTS (SELECT 1 FROM events e WHERE e.id = q.event_id);
  
  SELECT 'Sessions with invalid quiz' FROM quiz_sessions qs 
  WHERE NOT EXISTS (SELECT 1 FROM quizzes q WHERE q.id = qs.quiz_id);
  "
  ```

- [ ] **Demo User Validation**
  ```bash
  # Ensure demo user exists and password works
  python backend/scripts/seed_data.py
  ```

- [ ] **Configuration Audit**
  - [ ] `JWT_SECRET` is set in `.env`
  - [ ] `DB_PASSWORD` is correct in `.env`
  - [ ] `REDIS_HOST` is reachable
  - [ ] `ALLOWED_ORIGINS` includes production domain

- [ ] **Log Monitoring Setup**
  - [ ] Login failures logged and monitored
  - [ ] "Not found" errors tracked
  - [ ] Database connection errors alerted

### During Development

1. **Never hardcode IDs** - Always make them optional with auto-creation
2. **Always provide clear error messages** - Include context about what failed
3. **Validate foreign keys** - Check each FK before creating dependent entities
4. **Use cascading deletes cautiously** - Could orphan data if not careful
5. **Test failure paths** - Don't just test happy paths

### Error Message Standards

**Good** ✅
```json
{
  "detail": "Invalid session token - participant not found for token: abc123..."
}
```

**Bad** ❌
```json
{
  "detail": "Session token error"
}
```

---

## 6. Database Seeding Strategy

### Problem
- Password hashes can become corrupted
- Demo data might be inconsistent

### Solution
Create a robust seeding script that:
1. Checks if data already exists
2. Gracefully handles duplicates
3. Regenerates hashes if needed
4. Logs what was created

Current implementation: ✅ Already does this in `scripts/seed_data.py`

---

## 7. Critical Assumptions to Validate

| Assumption | Validation Query | Expected Result |
|-----------|-----------------|-----------------|
| "Every user has a tenant" | `SELECT COUNT(*) FROM users WHERE tenant_id IS NULL;` | 0 |
| "Every quiz has an event" | `SELECT COUNT(*) FROM quizzes WHERE event_id IS NULL;` | 0 |
| "Events are unique per tenant" | `SELECT COUNT(DISTINCT event_id), tenant_id FROM quizzes GROUP BY tenant_id;` | All should match |
| "Active users have active tenants" | `SELECT COUNT(*) FROM users u JOIN tenants t ON u.tenant_id = t.id WHERE u.is_active = TRUE AND t.is_active = FALSE;` | 0 |

---

## 8. Monitoring & Alerting Setup

### Recommended Alerts

```
1. Login Failure Rate > 5% in 1 hour
   → Action: Check password reset emails working

2. "Event not found" errors > 0 in 1 day
   → Action: Debug quiz creation logic

3. "Invalid join code" > 10 in 1 hour
   → Action: Educate users or improve code sharing UX

4. Database connection errors > 0
   → Action: Check DB availability & credentials

5. JWT errors > 1% of API requests
   → Action: Check JWT_SECRET is consistent
```

---

## 9. Quick Troubleshooting

### "Invalid email or password" (login fails)
1. Check user exists: `SELECT * FROM users WHERE email = 'user@example.com';`
2. Check tenant: `SELECT * FROM tenants WHERE id = (SELECT tenant_id FROM users WHERE email = 'user@example.com');`
3. Check is_active: Both user and tenant must have `is_active = 1`
4. Re-seed if demo: `python backend/scripts/seed_data.py`

### "Event not found" (quiz creation fails)
1. Fix: Backend now auto-creates events ✅
2. If still occurs: Check tenant_id in JWT token

### "Invalid join code" (audience join fails)
1. Host must start session first
2. Check session exists: `SELECT * FROM quiz_sessions WHERE status IN ('created', 'active');`
3. Check event.join_code is set: `SELECT * FROM events WHERE join_code IS NOT NULL;`

---

## 10. Deployment Checklist

```bash
# 1. Stop backend
pkill -f uvicorn

# 2. Pull latest code
git pull origin main

# 3. Run migrations
cd backend && alembic upgrade head

# 4. Reinstall deps (if needed)
pip install -r requirements.txt

# 5. Seed demo data
python scripts/seed_data.py

# 6. Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@swaya.me","password":"Demo1234"}'

# 7. Test quiz creation (with token from step 6)
curl -X POST http://localhost:8000/api/v1/quizzes/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Quiz"}'

# 8. Restart backend
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 &
```

---

## Summary: Likelihood of Future Failures

| Failure Type | Likelihood | Mitigation | Impact |
|--------------|-----------|-----------|--------|
| Login issues | 🟡 Medium | Daily monitoring | Blocks all users |
| Quiz creation | 🟢 Low | Auto-event creation ✅ | Blocks authoring |
| Session join | 🟢 Low | Clear error messages ✅ | Wrong join code = wrong message ✅ |
| Answer submit | 🟢 Low | State machine validates ✅ | User sees clear error |
| DB corruption | 🟡 Medium | Regular backups + integrity checks | Catastrophic |
| Config errors | 🟡 Medium | Pre-deploy validation | Blocks operations |

---

## Action Items

1. ✅ Fixed: Quiz creation auto-creates events
2. ⚠️ TODO: Add production monitoring for login failures
3. ⚠️ TODO: Add weekly database integrity script
4. ⚠️ TODO: Add pre-deployment health checks
5. ⚠️ TODO: Add detailed error context logging

