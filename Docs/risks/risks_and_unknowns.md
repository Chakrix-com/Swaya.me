# Risks and Unknowns — Final Status

All items derived strictly from code review and implementation results.

---

## 1. Sync vs Async Service Inconsistencies [RESOLVED]
- **Mitigation**: T1-J.
- **Action**: Dead sync service files deleted; `persistence/database.py` guarded with warnings.
- **Evidence**: `backend/features/quiz/` now only contains `*_async.py` files.

## 2. Tenant Isolation: Middleware vs Dependency [RESOLVED]
- **Mitigation**: T1-E.
- **Action**: Replaced thread-unsafe singleton with `ContextVar` for request-scoped `tenant_id`.
- **Evidence**: `broker/policies/tenant_isolation.py` verified in Suite C.

## 3. Missing DB-Level Uniqueness for Duplicate Answers [RESOLVED]
- **Mitigation**: T1-D.
- **Action**: Added `uq_answer_participant_question` unique constraint and performed data cleanup.
- **Evidence**: Verified via migration `20260421_2341`.

## 4. Hardcoded Absolute Paths [RESOLVED]
- **Mitigation**: T1-B.
- **Action**: Migrated all hardcoded paths to `AppSettings.uploads_base_dir`.
- **Evidence**: `main.py` and `proctoring.py` now use `settings.app.uploads_base_dir`.

## 5. SMTP Configuration Outside Pydantic Settings [RESOLVED]
- **Mitigation**: T1-C.
- **Action**: Migrated SMTP configuration to `SMTPSettings` in the Pydantic system.
- **Evidence**: `core/auth/email_service.py` no longer uses `os.getenv`.

## 6. Token Stored in localStorage (XSS Risk) [ACCEPTED RISK]
- **Mitigation**: T3-A (Deferred/High Effort).
- **Status**: JWT remains in `localStorage`. Standard for many SPAs but acknowledged as a security consideration.

## 7. python-socketio Listed But Not Active [RESOLVED]
- **Mitigation**: T1-F.
- **Action**: Removed unused dependencies from `requirements.txt`.
- **Evidence**: `TechnologiesUsed.md` updated to NOT ACTIVE.

## 8. Audience Session State Polling Mechanism [RESOLVED]
- **EVIDENCE**: Verified in pre-work. `AudienceSession.jsx:73-81` uses 2-second HTTP polling.

## 9. Proctoring Webcam Analysis is Frontend-Only [MITIGATED]
- **Mitigation**: T2-C.
- **Action**: Added server-side snapshot receipt validation to `submit_exam()`.
- **Evidence**: Submissions now rejected if proctoring is enabled but zero snapshots were received. Full server-side video analysis remains out of scope.

## 10. MediaPipe Models Loaded from External CDN [RESOLVED]
- **Mitigation**: T2-B.
- **Action**: Configured local hosting in `frontend/public/mediapipe/` and added `postinstall` download script.
- **Evidence**: `useFaceDetector.js` updated to local paths.

## 11. Ollama Dependency Not Versioned or Health-Checked [RESOLVED]
- **Mitigation**: T1-H.
- **Action**: Added `OllamaSettings` and a non-blocking connectivity check at application startup.
- **Evidence**: `main.py` logs Ollama status on startup.

## 12. No Rate Limiting Observed on Sensitive Endpoints [RESOLVED]
- **Mitigation**: T1-A.
- **Action**: Implemented `slowapi` rate limiting on `/register`, `/login`, and `/forgot-password`.
- **Evidence**: Verified decorators in `broker/api/auth.py`.

## 13. No DB-Level FK Constraints on Proctoring Tables [RESOLVED]
- **Mitigation**: T2-A.
- **Action**: Added `ForeignKey` constraints with `ondelete='CASCADE'`.
- **Evidence**: Verified via migration `20260421_2347`.

## 14. Tier Limit Counters Use Redis (Not DB) [RESOLVED]
- **Mitigation**: T1-G.
- **Action**: Added DB fallback to `check_participant_limit()` if Redis key is missing.
- **Evidence**: Logic updated in `core/config/tier_service.py`.

## 15. Exam Time Limit Not Enforced Server-Side [RESOLVED]
- **EVIDENCE**: Verified in pre-work. `exam_service_async.py:197-202` raises HTTP 410 if time limit exceeded.

## 16. Concurrent-Safe Session Restart [RESOLVED]
- **EVIDENCE**: Verified in pre-work. `session_service_async.py:594-621` invalidates participants on start.

## 17. `QuizFeedback` Has No Unique Constraint [RESOLVED]
- **Mitigation**: T1-I.
- **Action**: Added `uq_feedback_participant_session` unique constraint.
- **Evidence**: Verified via migration `20260421_2341`.
