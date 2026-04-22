# Risk Mitigation Plan — Swaya.me

## Context

17 risks were identified in `Docs/risks/risks_and_unknowns.md` from a code-only analysis. Before planning mitigations, a deep code exploration was done on every cited file. Two risks turned out to be already mitigated (Risks 15 and 16), and one was derivable from code (Risk 8). This plan addresses all 17.

---

## Pre-Work: Documentation Corrections (no code changes) [COMPLETED]

Update `Docs/risks/risks_and_unknowns.md` and `Docs/CLAUDE.md` to mark these as resolved:

- **Risk 15 (Exam time limit)** — [VERIFIED] ALREADY ENFORCED. `exam_service_async.py:197-202` inside `_get_active_participant()` checks `elapsed > quiz.exam_time_limit_seconds` → HTTP 410 before `submit_exam()` proceeds.
- **Risk 16 (Session restart)** — [VERIFIED] ALREADY HANDLED. `session_service_async.py:594-621` does a bulk `UPDATE Participant SET is_active=False` + Redis token eviction on session start.
- **Risk 8 (Audience polling)** — [VERIFIED] DERIVABLE FROM CODE. `AudienceSession.jsx:73-81` uses `setInterval(loadResults, 2000)` — 2-second HTTP polling. No WebSocket or SSE.

---

## Tier 1 — High Impact, Low Effort (implement first)

### T1-A: Rate Limiting on Auth Endpoints (Risk 12) [COMPLETED]
`slowapi` is already in `requirements.txt` but zero `@limiter` decorators exist anywhere.

**Files modified:**
- `backend/shared/utils/rate_limiter.py` [CREATED] — instantiate `Limiter` using the existing `redis_client` URL
- `backend/main.py` — register `SlowAPIMiddleware` and the 429 error handler
- `backend/broker/api/auth.py` — added decorators:
  - `POST /register` → `@limiter.limit("5/minute")`
  - `POST /login` → `@limiter.limit("10/minute")`
  - `POST /forgot-password` → `@limiter.limit("3/minute")`

**Pattern (from slowapi docs):**
```python
# shared/utils/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
```

---

### T1-B: Move Hardcoded Paths to Settings (Risk 4) [COMPLETED]
`main.py:33,38,111` and `broker/api/proctoring.py:269` hardcode `/home/vinay/Swaya.me/backend/uploads/...`.

**Files modified:**
- `backend/core/config/settings.py` — added `uploads_base_dir` field to `AppSettings`
- `backend/main.py` — replaced hardcoded paths with `Path(settings.app.uploads_base_dir)`
- `backend/broker/api/proctoring.py` — replaced hardcoded proctoring snapshot path with `settings.app.uploads_base_dir / "proctoring"`

---

### T1-C: Migrate SMTP Config to Pydantic Settings (Risk 5) [COMPLETED]
`core/auth/email_service.py` uses bare `os.getenv()` with its own `load_dotenv()` call.

**Files modified:**
- `backend/core/config/settings.py` — added `SMTPSettings` class and integrated into `Settings`
- `backend/core/auth/email_service.py` — removed `load_dotenv()`, replaced all `os.getenv()` calls with `settings.smtp.*` or `settings.app.environment`

---

### T1-D: Add DB-Level Unique Constraint on Answers (Risk 3) [COMPLETED]
SELECT-then-INSERT has a race condition window; no DB guard exists.

**Files modified:**
- `backend/persistence/models/quiz.py` — added `UniqueConstraint('participant_id', 'question_id', name='uq_answer_participant_question')` to `Answer` model
- **Alembic migration** `20260421_2341_add_unique_constraints_and_sync_metadata.py` [CREATED & APPLIED]
- [CLEANUP] Ran `cleanup_duplicate_answers.py` to remove 13 pairs of duplicate answers before applying constraint.

---

### T1-E: Replace TenantContext Singleton with ContextVar (Risk 2) [COMPLETED]
`broker/policies/tenant_isolation.py:21` — module-level singleton is not request-scoped.

**Files modified:**
- `backend/broker/policies/tenant_isolation.py` — replaced `TenantContext()` singleton with `ContextVar` based implementation for thread-safe request-scoped context.
- [CLEANUP] Removed unused `from persistence.database import get_db` import.

---

### T1-F: Remove Unused python-socketio Dependency (Risk 7) [COMPLETED]
Installed but has zero active route handlers. `routes.py` has a `# TODO: Include realtime routes` comment.

**Files modified:**
- `backend/requirements.txt` — removed `python-socketio==5.16.1` and `python-engineio==4.13.1`
- `TechnologiesUsed.md` — changed status to NOT ACTIVE (REMOVED)

---

### T1-G: Add Redis-to-DB Fallback for Tier Counters (Risk 14) [COMPLETED]
`tier_service.py:check_participant_limit()` reads `session:{id}:participants:count` from Redis with no fallback if key is absent after a Redis restart.

**Files modified:**
- `backend/core/config/tier_service.py` — updated `check_participant_limit()` to query DB `COUNT(*)` and repopulate Redis if the key is missing.

---

### T1-H: Move Ollama Config to Settings (Risk 11) [COMPLETED]
`core/ai/ollama_service.py:14-15` hardcodes URL and model name.

**Files modified:**
- `backend/core/config/settings.py` — added `OllamaSettings` class and integrated into `Settings`
- `backend/core/ai/ollama_service.py` — replaced hardcoded constants with `settings.ollama.*`
- `backend/main.py` — added non-blocking Ollama connectivity check at startup.

---

### T1-I: Add Unique Constraint on QuizFeedback (Risk 17) [COMPLETED]
No constraint prevents duplicate feedback submissions from the same participant.

**Files modified:**
- `backend/persistence/models/quiz.py` — added `UniqueConstraint('participant_id', 'session_id', name='uq_feedback_participant_session')` to `QuizFeedback` model
- **Alembic migration** (shared with T1-D)

---

### T1-J: Guard or Delete Legacy Sync Service Files (Risk 1) [COMPLETED]
`features/quiz/quiz_service.py`, `question_service.py`, `session_service.py`, `answer_service.py` are dead code.

**Files modified:**
- [DELETED] `backend/features/quiz/answer_service.py`
- [DELETED] `backend/features/quiz/question_service.py`
- [DELETED] `backend/features/quiz/quiz_service.py`
- [DELETED] `backend/features/quiz/session_service.py`
- `backend/persistence/database.py` — added explicit warning comment against application use.

---

## Tier 2 — Medium Effort (implement after Tier 1)

### T2-A: Add FK Constraints to Proctoring Tables (Risk 13) [COMPLETED]
`ProctoringSession`, `ProctoringEvent`, `TenantProctoringPolicy` use plain Integer columns with no FK constraints.

**Files modified:**
- `backend/persistence/models/proctoring.py` — added `ForeignKey` references with `ondelete='CASCADE'` for participant_id, quiz_id, and tenant_id.
- **Alembic migration** `20260421_2347_add_proctoring_fk_constraints.py` [CREATED & APPLIED]

---

### T2-B: Bundle MediaPipe Assets Locally (Risk 10) [COMPLETED]
WASM and `.tflite` model loaded from external CDNs; silently fails if CDN is unreachable.

**Files modified:**
- `frontend/public/mediapipe/wasm/` & `frontend/public/mediapipe/models/` [CREATED]
- `frontend/src/features/proctoring/hooks/useFaceDetector.js` — updated `FilesetResolver` and `modelAssetPath` to use local `/mediapipe/...` paths.
- `frontend/package.json` — added `postinstall` script to download assets using `curl`.


---

### T2-C: Add Server-Side Snapshot Receipt Validation (Risk 9) [COMPLETED]
Proctoring is entirely frontend-enforced. Minimum viable server-side check: require at least one snapshot upload before exam submission is accepted.

**Files modified:**
- `backend/features/proctoring/proctoring_service_async.py` — added `record_snapshot_receipt()` and `get_snapshot_count()` helper functions.
- `backend/broker/api/proctoring.py` — updated `upload_snapshot()` to call `record_snapshot_receipt()`.
- `backend/features/quiz/exam_service_async.py` — updated `submit_exam()` to reject submissions if proctoring is enabled but zero snapshots were received.

---

## Tier 3 — High Effort / Accepted Risk

### T3-A: Migrate JWT from localStorage to httpOnly Cookies (Risk 6)
**Effort:** High. Accept as known risk for now, or implement fully:
- Backend: `POST /auth/login` returns `Set-Cookie: token=...; HttpOnly; Secure; SameSite=Strict`
- `frontend/src/services/api.js` — remove localStorage token read, add `withCredentials: true`
- `frontend/src/store/authSlice.js` — remove all `localStorage.setItem('token', ...)` calls
- `main.py` CORS — set `allow_credentials=True`, restrict `allow_origins` to exact domain (not `*`)

### T3-B: Upgrade Audience Polling to SSE (Risk 8)
Current: 2-second `setInterval` HTTP polling in `AudienceSession.jsx:73-81`.
Defer unless server load becomes a problem. SSE requires new endpoint + Redis pub/sub wiring.

---

## Verification

After each Tier 1 item:
1. `pytest backend/` — existing tests must pass
2. Restart test backend: `sudo systemctl restart swayame-backend-test.service`
3. Smoke test on `test.swaya.me`: login, create quiz, join as audience, submit answer, run exam
4. **Rate limiting (T1-A)**: hit login 11 times in 1 minute → expect HTTP 429 on 11th request
5. **DB constraints (T1-D, T1-I)**: attempt duplicate answer via API → expect 400/409, NOT duplicate DB row

For each Alembic migration:
```bash
cd backend && .venv/bin/alembic upgrade head
```
Verify on test DB before promoting to live.

---

## Critical Files Reference

| Task | File(s) | Change |
|---|---|---|
| T1-A | `shared/utils/rate_limiter.py` (new), `main.py`, `broker/api/auth.py` | Add slowapi |
| T1-B | `core/config/settings.py`, `main.py:33,38,111`, `broker/api/proctoring.py:269` | Env var for paths |
| T1-C | `core/config/settings.py`, `core/auth/email_service.py` | SMTPSettings |
| T1-D | `persistence/models/quiz.py`, new migration | UniqueConstraint on answers |
| T1-E | `broker/policies/tenant_isolation.py` | ContextVar |
| T1-F | `requirements.txt`, `TechnologiesUsed.md` | Remove socketio |
| T1-G | `core/config/tier_service.py` | DB fallback for Redis counter |
| T1-H | `core/config/settings.py`, `core/ai/ollama_service.py`, `main.py` | OllamaSettings |
| T1-I | `persistence/models/quiz.py`, new migration | UniqueConstraint on feedback |
| T1-J | `features/quiz/quiz_service.py` + 3 others | Delete dead sync files |
| T2-A | `persistence/models/proctoring.py`, new migration | Add FKs |
| T2-B | `frontend/public/mediapipe/`, `useFaceDetector.js` | Bundle assets locally |
| T2-C | `proctoring_service_async.py`, `exam_service_async.py` | Snapshot counter check |
| T3-A | `main.py`, `authSlice.js`, `api.js`, `broker/api/auth.py` | httpOnly cookies |

---

## Final Status & Remaining Risks (2026-04-22)

### Mitigation Progress Summary
- **Pre-Work**: [COMPLETED]
- **Tier 1 (High Impact)**: [COMPLETED] (T1-A to T1-J)
- **Tier 2 (Medium Effort)**: [COMPLETED] (T2-A to T2-C)
- **Tier 3 (High Effort)**: [ACCEPTED RISKS] (T3-A, T3-B)

### Remaining Technical Risks
- **XSS Vulnerability (Risk 6)**: JWT tokens remain in `localStorage`. Full mitigation via `httpOnly` cookies was deferred as a Tier 3 high-effort task.
- **Frontend-Only Proctoring (Risk 9)**: While server-side receipt validation was added, the actual face/tab analysis remains frontend-enforced. A determined malicious actor could still bypass browser-side checks.
- **Audience Polling Overhead (Risk 8)**: The system relies on 2-second HTTP polling. Under extreme load, this will generate significant server traffic compared to SSE/WebSockets.

### Infrastructure & Environmental Risks
- **E2E Testing Stability**: Regression Suites D (Selenium) and E (Playwright) failed during verification due to local environment networking (Docker bridge routing) and browser timeout issues.
- **Port/Service Dependency**: The codebase contains several hardcoded references to port `8000`. Running the backend on alternative ports (e.g., 8001) requires multiple environment overrides and frontend rebuilds to maintain compatibility.
- **Host Header Sensitivity**: `uvicorn` or the local networking environment showed sensitivity to host headers (returning 400), requiring `TrustedHostMiddleware` to be carefully managed during cross-interface testing.
