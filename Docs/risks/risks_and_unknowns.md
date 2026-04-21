# Risks and Unknowns

All items derived strictly from code review. No assumptions.

---

## 1. Sync vs Async Service Inconsistencies

### Legacy Sync Files Not Deleted
- **Files**: `features/quiz/quiz_service.py`, `question_service.py`, `session_service.py`, `answer_service.py`
- **Risk**: Both sync and async implementations coexist. The sync versions are NOT removed. Any developer could accidentally import from the sync file.
- **Evidence**: `broker/api/quiz.py` imports only `*_service_async.py` variants; sync files have no active router imports visible in reviewed code. But sync `database.py` still exports a `get_db()` session dependency.
- **Impact**: Mixed sync/async usage within async FastAPI routes causes thread blocking and potential deadlocks.

### Tenant Isolation Middleware Uses Sync Import
- **File**: `broker/policies/tenant_isolation.py:8`
- `from persistence.database import get_db` — imports sync session factory
- The middleware does NOT actually call `get_db()` in any reviewed path; it only decodes JWT. However the import exists and could cause confusion.

---

## 2. Tenant Isolation: Middleware vs Dependency

### Module-Level Singleton Context
- **File**: `broker/policies/tenant_isolation.py:21`
- `tenant_context = TenantContext()` — module-level singleton
- Middleware sets `tenant_context.tenant_id` per request, but this is a global object, NOT request-scoped
- **Risk**: Under concurrent requests (uvicorn with multiple workers or async concurrent handling), one request's tenant_id could overwrite another's
- **Actual isolation**: Tenant isolation is correctly enforced in `get_current_user()` via DB lookup (fetches User+Tenant from JWT payload per request). The middleware context is auxiliary and appears unused in business logic.
- **Evidence**: `get_current_user()` in `core/auth/dependencies.py` does its own DB fetch — it does NOT read from `tenant_context`

---

## 3. Missing DB-Level Uniqueness for Duplicate Answers

- **File**: `features/quiz/answer_service_async.py`
- Duplicate answer prevention is a SELECT-then-INSERT pattern in application code
- No `UNIQUE` constraint on `(participant_id, question_id)` in `persistence/models/quiz.py`
- **Risk**: Under concurrent submissions (race condition), two identical answers from the same participant could be inserted
- **Impact**: Inflated answer counts; possible incorrect leaderboard scores

---

## 4. Hardcoded Absolute Paths

- **Files**: `backend/main.py` (lines 33-34, 39-40, 111), `backend/broker/api/proctoring.py` (line 269)
- Paths hardcoded: `/home/vinay/Swaya.me/backend/uploads/images`, `/uploads/temp`, `/uploads/proctoring/{quiz_id}/{participant_id}`
- **Risk**: Application fails immediately on any deployment that differs from this specific machine path
- **Impact**: Non-portable; deployment to any other VM or containerized environment requires code changes, not config changes

---

## 5. SMTP Configuration Outside Pydantic Settings

- **File**: `core/auth/email_service.py`
- SMTP vars read via `os.getenv()`, not through `settings` object
- **Risk**: Not validated at startup; no type coercion; no .env loading guarantee at module init time
- The file calls `load_dotenv()` directly, creating a secondary env loading path
- **Impact**: Email configuration errors are silently swallowed — `smtp_enabled = False` and emails are logged, not sent. No startup warning beyond a log message.

---

## 6. Token Stored in localStorage (XSS Risk)

- **File**: `frontend/src/store/authSlice.js`; `frontend/src/services/api.js`
- JWT stored in `localStorage['token']`; user object in `localStorage['user']`
- **Risk**: XSS attack can exfiltrate both token and user object
- **Standard mitigation** (httpOnly cookies) is not used
- **Scope**: Standard for SPAs but noted as a security consideration

---

## 7. python-socketio Listed But Not Active

- **TechnologiesUsed.md**: lists `python-socketio==5.16.1` as HIGH confidence
- **Evidence in code**: `broker/api/routes.py` has comment `# TODO: Include realtime routes`
- **NOT DERIVABLE**: No active socketio route handlers found in reviewed files
- **Risk**: Listed as a dependency but no real-time socketio is available to users. Audience polling mechanism for session state is NOT DERIVABLE from reviewed code (the SSE endpoint exists only for whiteboard, not main session state).

---

## 8. Audience Session State Polling Mechanism Unclear

- **NOT DERIVABLE FROM CODE**: The exact mechanism by which `AudienceSession` receives question advances is not provable from reviewed files
- `AudienceSession.jsx` was not fully reviewed — the polling interval/SSE mechanism for session state is unknown
- The SSE endpoint at `/quizzes/sessions/{id}/whiteboard-events/public` exists for whiteboard only
- There is a Redis key `session:{id}:state` written by `session_service_async.py` but the polling API endpoint name for audience state is NOT DERIVABLE from reviewed route code

---

## 9. Proctoring Webcam Analysis is Frontend-Only

- **Risk**: Webcam monitoring (face detection, stream end) is implemented entirely in the browser using MediaPipe
- No server-side video analysis
- Participant can bypass face detection by modifying JavaScript or running in a non-standard browser environment
- **Evidence**: `useFaceDetector.js` runs entirely in browser; only reports violations to backend — backend does not perform independent verification
- Snapshots are uploaded but no OCR/face recognition on server side is visible in reviewed code

---

## 10. MediaPipe Models Loaded from External CDN

- **File**: `frontend/src/features/proctoring/hooks/useFaceDetector.js`
- WASM loaded from: `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/wasm`
- Model from: `https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite`
- **Risk**: External CDN dependency — if CDN is unavailable, face detection silently fails (caught with empty catch). Proctoring will not function without internet access to these CDNs from the participant's browser.

---

## 11. Ollama Dependency Not Versioned or Health-Checked

- **File**: `core/ai/ollama_service.py`
- Hardcoded URL: `http://127.0.0.1:11434`
- Default model: `qwen2.5:3b` — must be pre-pulled on the server
- No health check at startup; AI endpoints return 503 if Ollama is not running
- **Risk**: AI features silently unavailable without the Ollama daemon and specific model weights on the host machine

---

## 12. No Rate Limiting Observed on Sensitive Endpoints

- `slowapi` is in requirements but no `@limiter.limit()` decorators were observed on auth endpoints in reviewed code
- **Specifically**: `POST /auth/login`, `POST /auth/register`, `POST /auth/forgot-password` show no rate limiting in `broker/api/auth.py`
- **Risk**: Brute-force attacks on login, email enumeration via forgot-password (mitigated in code by always returning 200, but timing attacks remain possible)

---

## 13. No DB-Level FK Constraints on Proctoring Tables

- **File**: `persistence/models/proctoring.py`
- `ProctoringSession.participant_id`, `.quiz_id`, `.tenant_id` — plain Integer columns, no FK constraints
- `ProctoringEvent` — same: no FK constraints
- `TenantProctoringPolicy.tenant_id` — no FK
- **Risk**: Orphaned records possible if participants or quizzes are deleted; no cascade behavior
- **Evidence**: Comments not present; this appears intentional for performance, but it means data integrity is enforced only at application level

---

## 14. Tier Limit Counters Use Redis (Not DB)

- **File**: `core/config/tier_service.py`
- `check_participant_limit()` reads `session:{session_id}:participants:count` from Redis
- `increment_participant_count()` increments Redis counter
- **Risk**: If Redis is restarted/flushed, participant count counters reset to 0, bypassing tier limits until the next join
- No reconciliation against actual DB participant count exists in reviewed code

---

## 15. Exam Time Limit Not Enforced Server-Side

- **File**: `broker/api/exam.py`, `features/quiz/exam_service_async.py`
- `exam_time_limit_seconds` stored in DB; returned to frontend in `ExamStartResponse`
- Timer countdown is frontend-only (`ExamSession.jsx`)
- **Risk**: A participant who modifies the frontend or uses a direct API call can submit after the time limit has expired
- The `submit_exam()` endpoint does not check `started_at + time_limit_seconds < now()`
- **Evidence**: NOT DERIVABLE if there is any server-side time check in `exam_service_async.py` (file not fully reviewed) — flagged as risk pending full review

---

## 16. Concurrent-Safe Session Restart

- `join_session()` sets `participant.is_active=True` and caches `is_active` in Redis
- When session is restarted, existing participants' `is_active` must be set to False in both DB and Redis
- **NOT DERIVABLE**: The exact mechanism for marking existing participants inactive on restart is not proven in reviewed code. Only the check (`if not participant.is_active → 403`) and the Redis cache structure are visible.

---

## 17. `QuizFeedback` Has No Unique Constraint

- **File**: `persistence/models/quiz.py`
- No constraint preventing a single participant from submitting multiple feedback entries for the same quiz/session
- Enforcement, if any, is in `feedback_service_async.py` (not reviewed in full)
- **NOT DERIVABLE**: Whether duplicate feedback is prevented at service level
