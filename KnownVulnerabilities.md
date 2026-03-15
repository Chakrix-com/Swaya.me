# Known Vulnerabilities

This document captures confirmed security vulnerabilities identified in the codebase audit.

## 1) Authentication bypass for demo account (Critical)

- **Finding:** Email verification is bypassed for a hardcoded account.
- **Location:** `backend/core/auth/service_async.py` (`DEMO_LOGIN_BYPASS_EMAIL`, `bypass_email_verification` logic).
- **Impact:** If credentials are known/compromised, unverified login is possible, weakening auth policy.
- **Recommendation:** Remove hardcoded bypass; enforce verification uniformly across all accounts.

## 2) Unauthenticated session result exposure / IDOR (High)

- **Finding:** Session/question results endpoints can be queried without host auth and expose sensitive result data.
- **Location:** `backend/broker/api/quiz.py` (`/sessions/{session_id}/results`, `/sessions/{session_id}/leaderboard`), `backend/features/quiz/answer_service_async.py`.
- **Impact:** Unauthorized users can enumerate `session_id` values and retrieve quiz outcomes, participant-related data, and answer correctness metadata.
- **Recommendation:** Require authorization and ownership checks (host or valid participant scoped to session); avoid returning privileged fields publicly.

## 3) Path traversal in temp image handling (High)

- **Finding:** `temp_key` is used directly in filesystem paths for move/delete operations without strict filename sanitization.
- **Location:** `backend/core/storage/image_service.py` (`move_temp_to_permanent`, `delete_temp_image`), called from `backend/broker/api/uploads.py`.
- **Impact:** Crafted `temp_key` values may allow file operations outside intended temp directories.
- **Recommendation:** Validate with strict allowlist (`^[a-zA-Z0-9._-]+$`), reject separators, and resolve+verify path stays under tenant temp directory.

## 4) Missing effective rate limiting on sensitive endpoints (High)

- **Finding:** Login/join/answer endpoints are not actively rate-limited in API wiring.
- **Location:** `backend/broker/api/auth.py`, `backend/broker/api/quiz.py`, and missing limiter integration in `backend/main.py`.
- **Impact:** Increased risk of brute-force, credential stuffing, join-code guessing, and answer spam/abuse.
- **Recommendation:** Enforce per-IP and per-identity limits on auth and participant endpoints; add abuse telemetry and temporary lockouts.

## 5) Session tokens passed via query parameters (Medium)

- **Finding:** Participant `session_token` is sent as query param for multiple endpoints.
- **Location:** `backend/broker/api/quiz.py` and `frontend/src/services/api.js`.
- **Impact:** Tokens may leak through access logs, browser history, reverse proxies, and referrer headers.
- **Recommendation:** Move tokens to `Authorization` header (Bearer) or secure POST body transport with minimized logging.

## 6) Hardcoded credentials in repository scripts/tests (Medium)

- **Finding:** Several test/util scripts include plaintext credentials.
- **Examples:** `test_word_cloud_e2e.py`, `test_rejoin_flow.py`, `scripts/capture_*.py`, `run_high_load_test.sh`, `run_incremental_load_test.sh`.
- **Impact:** Credential leakage risk and insecure operational hygiene.
- **Recommendation:** Replace with environment variables/secrets management; rotate any real credentials immediately.

---

## Notes from dependency checks

- Root `npm audit` reported no production vulnerabilities.
- Frontend `npm audit` could not complete due registry audit endpoint limitations in the current environment.
- Python `pip-audit` was unavailable in the current environment and could not be executed.
