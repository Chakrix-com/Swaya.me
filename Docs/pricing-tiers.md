# Pricing Tiers & Feature Entitlements

## Overview

Swaya.me implements a **multi-tenant SaaS** pricing model with configurable tier-based limits. Limits are stored in the `tier_configurations` DB table, cached in Redis for 5 minutes per tier, and enforced at runtime by `TierService`.

Last updated: April 2026

---

## Tier Structure

| Tier | Target Audience | Typical Use Case |
|------|----------------|------------------|
| **Free** | Individual educators, small teams | Classroom quizzes, ad-hoc team meetings |
| **Basic** | Growing teams, regular users | Weekly standups, workshops |
| **Pro** | Professional users, frequent events | Client presentations, training sessions |
| **Enterprise** | Large organisations, custom needs | Company-wide deployment |

---

## Current Enforced Limits

These are the live values in the production `tier_configurations` table:

| Tier | Participants / session | Questions / quiz | Concurrent sessions |
|------|----------------------|-----------------|-------------------|
| **Free** | 100 | 10 | 1 |
| **Basic** | 250 | 30 | 2 |
| **Pro** | 2,500 | 100 | 5 |
| **Enterprise** | 10,000 | 1,000 | 50 |

Limits can be updated by a super_admin at `/admin/tier-management` (UI) or directly via `PUT /admin/tier-configs/{tier}` (API). Changes take effect after Redis TTL expires (≤ 5 min).

---

## Feature Availability Matrix

All question types and quiz modes are available on all tiers. Tier limits apply only to quotas (participants, questions, concurrent sessions).

| Feature | Free | Basic | Pro | Enterprise |
|---------|------|-------|-----|------------|
| Quiz mode (live scored) | ✅ | ✅ | ✅ | ✅ |
| Poll mode (live unscored) | ✅ | ✅ | ✅ | ✅ |
| Exam mode (self-paced) | ✅ | ✅ | ✅ | ✅ |
| Offline Poll | ✅ | ✅ | ✅ | ✅ |
| MCQ questions | ✅ | ✅ | ✅ | ✅ |
| Word Cloud questions | ✅ | ✅ | ✅ | ✅ |
| One Word questions | ✅ | ✅ | ✅ | ✅ |
| Single Line / Paragraph | ✅ | ✅ | ✅ | ✅ |
| Scale questions | ✅ | ✅ | ✅ | ✅ |
| Per-question timer | ✅ | ✅ | ✅ | ✅ |
| Image upload (questions & options) | ✅ | ✅ | ✅ | ✅ |
| Question reordering | ✅ | ✅ | ✅ | ✅ |
| Export (XLSX, PDF, DOCX, PPTX) | ✅ | ✅ | ✅ | ✅ |
| Leaderboard | ✅ | ✅ | ✅ | ✅ |
| Presenter view | ✅ | ✅ | ✅ | ✅ |
| QR code join | ✅ | ✅ | ✅ | ✅ |
| Template library | ✅ | ✅ | ✅ | ✅ |
| Folder organisation | ✅ | ✅ | ✅ | ✅ |
| Excel import | ✅ | ✅ | ✅ | ✅ |
| 11-language UI | ✅ | ✅ | ✅ | ✅ |
| Profanity filter | ✅ | ✅ | ✅ | ✅ |

---

## Quota Enforcement

### Participant limit
Checked at session join time. If participant count exceeds `max_participants`, the join request is rejected with 403.

### Question limit
Checked at quiz publish time. A quiz with more questions than `max_questions` cannot be published.

### Concurrent session limit
Checked at session start time. If active session count for the tenant meets `max_concurrent_events`, the start request is rejected.

### Cache
`TierService` caches per-tier config in Redis with a 5-minute TTL. After a super_admin updates limits, the cache key `tier_config:{tier}` is invalidated on next read.

---

## UI Tier Indicators

### Tier badge (header)
- Shown to authenticated hosts in the top navigation bar
- Colour: grey (Free), blue (Basic), purple (Pro), gold (Enterprise)
- Hover tooltip shows live limits: participants/session, questions/quiz, concurrent sessions
- Tooltip labels translated in all 11 languages

### Upgrade banner (Dashboard)
- Always shown to Free users regardless of usage
- Shown to Basic/Pro users when quiz usage ≥ 70% of `max_questions`
- Displays current tier limits and next tier's limits
- Dismissible for 3 days (stored in `localStorage`)

---

## Admin Tier Management

- **View limits**: any authenticated user via `GET /auth/my-limits`
- **View all tiers**: any authenticated user via `GET /auth/tier-plans`
- **Update limits**: super_admin only via `PUT /admin/tier-configs/{tier}` (requires all 3 fields)
- **Change user tier**: super_admin via Edit User on `/admin/users`
- User tier displayed as colour-coded badge in the user management table and edit form

---

## Scalability Path

The tier system is fully configurable without code changes:
- Limits stored in DB → editable by super_admin at runtime
- Redis cache means changes propagate within 5 minutes
- New tiers can be added by extending the `TierEnum` and adding a row to `tier_configurations`
