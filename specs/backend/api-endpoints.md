# API Endpoint Specs — New Endpoints

**Date:** 2026-06-13  
**Status:** All endpoints implemented  
**Base URL:** `/api/v1/quizzes`

---

## 1. Home Stats Aggregate

**Purpose:** Aggregate session/participant/score data for the logged-in host's home page.

**Route:** `GET /sessions/home-stats`  
**Auth:** Bearer JWT (any authenticated user)  
**Params:** None  

**Response (`HomeStatsResponse`):**
```json
{
  "sessions_this_week": 3,
  "participants_this_week": 142,
  "avg_score_this_week": 78.4,
  "last_session": {
    "quiz_id": 1014,
    "quiz_title": "Tech Trivia",
    "quiz_type": "quiz",
    "session_id": 502,
    "ended_at": "2026-06-12T14:32:00",
    "participant_count": 47,
    "avg_score": 78.0
  }
}
```

**Notes:**
- Scoped to `current_user.tenant_id` — never leaks cross-tenant data.
- "This week" = last 7 calendar days, not ISO week.
- `avg_score_this_week` and `last_session` may be `null` if no sessions in window.
- Used by: `frontend/src/features/dashboard/Dashboard.jsx` stats row.

---

## 2. Cross-Quiz Sessions Listing (Results Hub)

**Purpose:** Paginated list of all sessions across all quizzes for a tenant, filterable by quiz type and status.

**Route:** `GET /sessions/all`  
**Auth:** Bearer JWT (any authenticated user)  
**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `page` | int | 1 | 1-indexed |
| `page_size` | int | 20 | Max 100 |
| `quiz_type` | enum | — | `quiz`, `poll`, `exam`, `offline_poll` |
| `status` | enum | — | `created`, `active`, `ended` |

**Response (`ResultsHubResponse`):**
```json
{
  "items": [
    {
      "session_id": 502,
      "quiz_id": 1014,
      "quiz_title": "Tech Trivia",
      "quiz_type": "quiz",
      "status": "ended",
      "participant_count": 47,
      "started_at": "2026-06-12T14:00:00",
      "ended_at": "2026-06-12T14:32:00",
      "avg_score": 78.0
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20
}
```

**Notes:**
- Scoped to tenant. `super_admin` sees all tenants' sessions.
- Used by: `frontend/src/features/quiz/ResultsHub.jsx`.
- Ordered by `started_at DESC`.

---

## 3. Per-Candidate Integrity Detail

**Purpose:** Full proctoring event log for a single exam participant (host-only).

**Route:** `GET /sessions/{session_id}/integrity/{participant_id}`  
**Auth:** Bearer JWT (host or admin of the tenant that owns this session)  
**Path params:** `session_id` (int), `participant_id` (int)

**Response:**
```json
{
  "participant_id": 123,
  "display_name": "Priya R.",
  "email": "priya@example.com",
  "score": 85,
  "integrity_score": 92,
  "flags": [
    {
      "event_type": "tab_switch",
      "occurred_at": "2026-06-12T10:15:33",
      "question_index": 3,
      "detail": null
    },
    {
      "event_type": "webcam_absent",
      "occurred_at": "2026-06-12T10:17:02",
      "question_index": 4,
      "detail": "duration_seconds: 8"
    }
  ],
  "snapshots": [
    {
      "url": "/api/uploads/images/proctoring/session_502/participant_123_q4.jpg",
      "question_index": 4,
      "taken_at": "2026-06-12T10:17:10"
    }
  ]
}
```

**Notes:**
- Used by: `frontend/src/features/quiz/IntegrityReport.jsx`.
- `integrity_score` is 0–100 (100 = no flags; deducted per flag type).
- Snapshots are served from `/api/uploads/images/proctoring/`.

---

## 4. Pre-Join Code Lookup

**Purpose:** Return quiz metadata to the join page before a participant enters their name — so they know they're joining the right activity.

**Route:** `GET /sessions/lookup`  
**Auth:** None (public endpoint)  
**Query params:**

| Param | Type | Required | Notes |
|---|---|---|---|
| `join_code` | string | Yes | 6-character alphanumeric |

**Response (`SessionLookupResponse`):**
```json
{
  "quiz_title": "Tech Trivia — Team Energiser",
  "quiz_type": "quiz",
  "participant_count": 12,
  "skin": "party"
}
```

**Error responses:**

| Code | When |
|---|---|
| 404 | `join_code` does not match any active session |
| 400 | Malformed `join_code` |

**Notes:**
- `skin` may be `null` (default skin).
- `participant_count` is the live count from Redis.
- Used by: `frontend/src/features/audience/AudienceJoin.jsx` — shown as subtitle on the join form so participants can verify they're in the right room.
- No auth required — intentionally public so anonymous participants can look up before entering their name.

---

## Endpoint auth summary

| Endpoint | Auth |
|---|---|
| `GET /sessions/home-stats` | JWT — any role |
| `GET /sessions/all` | JWT — any role; super_admin sees all tenants |
| `GET /sessions/{id}/integrity/{pid}` | JWT — host/admin of owning tenant |
| `GET /sessions/lookup` | None (public) |
