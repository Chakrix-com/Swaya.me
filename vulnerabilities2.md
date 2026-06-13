# Security Vulnerability Report — Swaya.me (test.swaya.me)

**Date:** 2026-06-13  
**Scope:** Full codebase audit after first-round fixes  
**Audited by:** Static code review of all backend API routes, services, middleware, and frontend  
**Severity levels:** Critical → High → Medium → Low → Informational

---

## CRITICAL

### VULN-01 · Proctoring Webcam Snapshots Served Unauthenticated via Static Mount

**File:** `backend/main.py:144`

The entire `uploads/` directory — including `uploads/proctoring/` which stores webcam snapshots of exam participants — is mounted as a public static file server with no authentication:

```python
app.mount("/api/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")
```

The `list_snapshots` endpoint at `GET /proctoring/snapshots/{quiz_id}/{participant_id}` returns URLs like `/api/uploads/proctoring/{quiz_id}/{participant_id}/{filename}.jpg`. Anyone who knows (or guesses) a valid `quiz_id`, `participant_id`, and filename can fetch webcam photos of exam participants directly — no authentication required.

Participant IDs are sequential integers. Quiz IDs are also sequential. Filenames are timestamps. An attacker can enumerate these trivially.

**Impact:** Sensitive biometric data (participant faces) exposed to any internet user without authentication.

**Fix:** Either (a) do not store webcam snapshots under the public static mount — use a separate protected directory outside `uploads/` — or (b) add an nginx `auth_request` directive that proxies to the API for authentication before serving files under `/api/uploads/proctoring/`. Option (b) requires nginx-side changes. Option (a) is simpler: change `svc.record_snapshot_receipt` to write to a path outside the static mount (e.g., `backend/proctoring_snaps/`) and add a separate authenticated endpoint to serve them.

---

## HIGH

### VULN-02 · Insecure OTP Generation (Non-CSPRNG)

**File:** `backend/features/quiz/exam_service_async.py:158`

Exam OTPs are generated using Python's non-cryptographic `random` module:

```python
otp = str(random.randint(100000, 999999))
```

`random.randint` is seeded from the system clock and its state can be predicted if an attacker can observe multiple OTP values or timing. This is in contrast to the session join code (which correctly uses `secrets.choice`) and participant tokens (which use `secrets.token_urlsafe`).

The OTP has only 900,000 possible values (100000–999999) and the rate limit is 3 OTPs per 10 minutes *per email per slug*. An attacker who targets a specific exam slug without knowing the victim email could brute-force a short-lived OTP from a small keyspace using the predictable PRNG.

**Impact:** OTP forgery allows impersonating an exam participant, bypassing OTP email verification, and registering under another participant's email.

**Fix:**
```python
import secrets
otp = str(secrets.randbelow(900000) + 100000)
```

---

### VULN-03 · Missing Authentication on Word Cloud Results Endpoint

**File:** `backend/broker/api/quiz.py:1017-1028`

The endpoint `GET /quizzes/questions/{question_id}/word-cloud-results` has no authentication or authorization check:

```python
@router.get("/questions/{question_id}/word-cloud-results", response_model=WordCloudResultsResponse)
async def get_word_cloud_results(
    question_id: int,
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    service: AnswerServiceAsync = Depends(get_answer_service)
):
    """Get word cloud results for a question"""
    try:
        return await service.get_word_cloud_results(db, session_id, question_id)
```

There is no `current_user = Depends(get_current_user)` or `session_token` validation. Any unauthenticated caller who knows `session_id` and `question_id` can retrieve all submitted word cloud answers for any session belonging to any tenant.

**Impact:** Participant text responses are exposed to anyone, cross-tenant. This leaks potentially sensitive audience responses from all organizations.

**Fix:** Add `current_user: CurrentUser = Depends(get_current_user)` and validate that the session belongs to `current_user.tenant_id`. Alternatively, accept a participant `session_token` for the participant-facing use case with appropriate validation.

---

### VULN-04 · Proctoring Lock/Unlock Lacks Tenant Isolation

**File:** `backend/broker/api/proctoring.py:373-395`

The endpoints `POST /proctoring/lock/{session_token}` and `POST /proctoring/unlock/{session_token}` authenticate the caller but do not verify that the session_token belongs to a participant in the calling admin's tenant:

```python
@router.post("/lock/{session_token}")
async def lock_session(
    session_token: str,
    current_user: CurrentUser = Depends(get_current_user),
    ...
):
    """Admin — manually lock a participant session."""
    await svc.lock_session(session_token, "ADMIN_LOCK", db, redis)
```

The `svc.lock_session` function (`backend/features/proctoring/proctoring_service_async.py:271`) resolves the participant from Redis state but never checks that `redis_data["tenant_id"] == current_user.tenant_id`.

**Impact:** Any authenticated user (even a regular `user` role — the endpoint only requires `get_current_user`, not `require_admin`) can lock or unlock the exam session of a participant from a different tenant, denying them access to their exam or reinstating a legitimately-locked cheater.

**Fix:** (1) Add `require_admin` dependency instead of `get_current_user`. (2) After resolving `redis_data`, add:
```python
if redis_data.get("tenant_id") != current_user.tenant_id:
    raise HTTPException(status_code=403, detail="Forbidden")
```

---

### VULN-05 · Excel Import Creates Quiz Questions Without Sanitization

**File:** `backend/features/quiz/import_service.py:225-253`

The `create_from_import` method inserts question text and option text from the uploaded XLSX directly into the database without any XSS sanitization or content filtering:

```python
question = Question(
    quiz_id=quiz.id,
    question_type=q_type,
    text=q["text"],      # raw from spreadsheet
    order=idx,
    options=db_options,  # raw from spreadsheet
    ...
)
```

Questions created via the normal API endpoint go through `sanitize_html(request.text)` and `check_content()` in `question_service_async.py:94-100`. The Excel import path bypasses both. Since question `text` is rendered via `dangerouslySetInnerHTML` in `RichTextRenderer.jsx:66`, malicious HTML in an imported spreadsheet would execute as XSS in the host's dashboard (QuizControl) and participant views.

**Impact:** Stored XSS targeting the quiz host's browser and participants. Can exfiltrate the host's HttpOnly cookie via subdomain-scoped XSS vectors, steal CSRF tokens, or perform arbitrary actions.

**Fix:** Apply the same sanitization pipeline in `create_from_import`:
```python
from shared.utils.html_sanitizer import sanitize_html, sanitize_plain
text=sanitize_html(q["text"]),
options=[sanitize_plain(o) for o in db_options],
```

---

### VULN-06 · HTML Injection in Exam OTP and Results Emails

**File:** `backend/features/quiz/exam_service_async.py:162-178`, `1001-1019`

Both the OTP email and results email embed unsanitized user-controlled data directly into HTML email bodies:

```python
html_body = f"""
  <p>Hi {display_name},</p>
  <p>Use the code below to start your exam <strong>{quiz.title}</strong>:</p>
```

`display_name` comes from unauthenticated user input (the exam start request body). `quiz.title` is host-controlled but also not escaped. A participant can supply a `display_name` containing `<script>` tags or phishing content that is embedded verbatim in the HTML email sent to their own email address.

While email clients typically strip `<script>`, this still enables:
- Email HTML injection: injecting content such as fake login forms into the OTP email
- If the email client renders inline styles/images, information exfiltration via pixel tracking

**Impact:** HTML injection in transactional emails; potential phishing via email body manipulation.

**Fix:** HTML-escape all user-controlled values before embedding in email HTML:
```python
import html
safe_name = html.escape(display_name)
safe_title = html.escape(quiz.title)
html_body = f"<p>Hi {safe_name},</p><p>Exam: <strong>{safe_title}</strong>...</p>"
```

---

### VULN-07 · Unused Vulnerable Dependency: `python-jose==3.3.0`

**File:** `backend/requirements.txt:126`

`python-jose==3.3.0` is present in `requirements.txt` but is not imported anywhere in the application code (the app uses `PyJWT` instead). `python-jose 3.3.0` has **CVE-2024-33664** (algorithm confusion attack allowing JWT forgery) and **CVE-2024-33663** (ECDSA key confusion). Even though the package is not actively used, it is installed in the venv and any future import could introduce the vulnerability.

Additionally, `cryptography==41.0.7` is pinned in requirements.txt but the running venv has `47.0.0` installed (from `pip show`). The pinned version 41.x has several older CVEs including RSA vulnerability variants. The mismatch between requirements.txt and installed version indicates dependency management inconsistency.

**Impact:** Risk of accidental use of vulnerable JWT library; potential for algorithm confusion attacks if `python-jose` is imported by a new code path.

**Fix:** Remove `python-jose` from `requirements.txt` entirely since `PyJWT` handles all JWT operations. Update `cryptography` pin to `>=43.0.0` (latest stable) in `requirements.txt`.

---

## MEDIUM

### VULN-08 · User Profile Data Stored in `localStorage` (XSS-Accessible Session Info)

**File:** `frontend/src/store/authSlice.js:4,23,36`

While the JWT itself is correctly stored in an HttpOnly cookie, the user profile object (including `tenant_id`, `role`, `tier`, `email`, `full_name`) is stored in `localStorage`:

```javascript
const initialState = {
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  isAuthenticated: !!localStorage.getItem('user'),
  ...
}
// On login:
localStorage.setItem('user', JSON.stringify(action.payload.user))
```

`localStorage` is accessible to any JavaScript running on the page. While XSS in the main question content path is now sanitized, any future XSS introduced anywhere on the site (e.g., a third-party widget, a new unsanitized field) can read the user's role, tenant ID, and email from localStorage.

**Impact:** Session metadata exfiltration. Depending on what the attacker can infer from the role/tenant_id, this supports privilege mapping and targeted attacks. Does not directly leak the JWT (which is properly HttpOnly).

**Fix:** Remove user profile from localStorage. Instead, re-fetch user state from the `/auth/me` API endpoint on page load (which is authenticated via the HttpOnly cookie). The Redux store can hold the profile in-memory only.

---

### VULN-09 · Exam Session Token Persisted in `localStorage`

**File:** `frontend/src/features/exam/ExamSession.jsx:912`

The exam participant's `session_token` is written to `localStorage` for crash recovery:

```javascript
localStorage.setItem(`exam_session_${slug}`, JSON.stringify({ sessionToken: data.session_token }))
```

The `session_token` is the only credential allowing a participant to submit/read exam answers. It is stored in `localStorage` where it is accessible to any JavaScript on the page, unlike the host's JWT which is in an HttpOnly cookie.

**Impact:** If XSS occurs on any page the participant visits while taking an exam, their session token can be exfiltrated and used by an attacker to submit answers on their behalf, read their progress, or view answer explanations.

**Fix:** Use `sessionStorage` instead of `localStorage` (survives page refresh but not tab close — the tab crash scenario is rarer), or store the token in a short-lived `sessionStorage` item with a server-side expiry check. Alternatively, accept the risk as low-probability for an exam-taking session and remove the crash recovery feature.

---

### VULN-10 · AI Endpoints Lack Rate Limiting

**File:** `backend/broker/api/ai.py`

The AI generation endpoints — `POST /ai/generate/questions`, `POST /ai/generate/options`, `POST /ai/generate/poll-prompt`, `POST /ai/rewrite` — have no per-endpoint rate limiting. Only `/auth/register`, `/auth/login`, and `/auth/forgot-password` have `@limiter.limit(...)` decorators.

A valid authenticated user can send thousands of requests per second to Gemini/Ollama generation endpoints, exhausting API quota (costing money) and causing denial of service for all other users.

**Impact:** API cost abuse (Gemini billing), resource exhaustion, denial of service for other users.

**Fix:** Add rate limits appropriate to paid API costs:
```python
@router.post("/generate/questions")
@limiter.limit("20/minute")
async def api_generate_questions(request: Request, ...):
```

---

### VULN-11 · Missing Rate Limiting on Join, Submit-Answer, and OTP Endpoints

**File:** `backend/broker/api/quiz.py`, `backend/broker/api/exam.py`

The following high-traffic, unauthenticated endpoints have no rate limiting:
- `POST /quizzes/sessions/join` — participant join (no auth)
- `POST /quizzes/sessions/submit-answer` — answer submission (only session token)
- `POST /quizzes/sessions/submit-word-cloud` — answer submission
- `POST /e/{slug}/request-otp` — has per-email-per-slug limiting in Redis but no IP-based global rate limit
- `POST /e/{slug}/start` — exam start (no auth)
- `POST /offline-poll/{slug}/join`, `/answer`, `/complete` — all public, no rate limit

An attacker can flood these endpoints to simulate many participants, exhaust database connections, or send enormous numbers of OTP emails if they enumerate valid `slug` values.

**Impact:** Resource exhaustion, email sender reputation damage from OTP spam, denial of service for legitimate participants.

**Fix:** Apply `@limiter.limit("60/minute")` or similar to participant-facing endpoints. For OTP, supplement the existing Redis limit with an IP-based global limit: `@limiter.limit("10/minute")`.

---

### VULN-12 · Admin-Only Role Check Using String Comparison Against Enum (stats_history)

**File:** `backend/broker/api/stats_history.py:38,56,98`

The stats history endpoint checks roles by comparing the `UserRole` enum to string literals:

```python
if current_user.user.role not in ['admin', 'super_admin']:
    raise HTTPException(status_code=403, detail="Admin access required")
if current_user.user.role == 'super_admin':
    ...
if current_user.user.role != 'super_admin':
    raise HTTPException(status_code=403, detail="Super admin access required")
```

Since `UserRole` inherits from `str`, the comparisons against string literals (`'admin'`, `'super_admin'`) work correctly at runtime (confirmed via test). However, the pattern is inconsistent with the rest of the codebase which uses `UserRole.admin` enum members. Future refactoring (e.g., changing enum values) would silently break this check without a type error.

**Impact:** Low immediate risk (comparison works correctly today), but brittle pattern that can lead to authorization bypass after enum value refactoring.

**Fix:** Replace string literals with enum members, or use the shared `require_admin`/`require_super_admin` dependencies:
```python
from core.auth.dependencies import require_super_admin
_: CurrentUser = Depends(require_super_admin)
```

---

### VULN-13 · Internal Tenant ID Leaked in Error Message

**File:** `backend/core/auth/service_async.py:221`

When a user's tenant record is missing from the database, the error message includes the actual tenant ID:

```python
raise TenantNotFoundError(f"User's tenant not found. Contact support (tenant_id: {user.tenant_id})")
```

This exception bubbles up to the login endpoint as a 401/422 HTTP response detail, leaking an internal database ID to the client.

**Impact:** Low — internal ID disclosure. Useful for attackers to understand the platform's internal numbering scheme and to target specific tenants.

**Fix:** Remove the tenant_id from the user-facing error message. Log it server-side at ERROR level instead:
```python
logger.error("Tenant not found for user %s tenant_id=%s", user.id, user.tenant_id)
raise TenantNotFoundError("Your organization account could not be found. Contact support.")
```

---

### VULN-14 · AI Service Error Details May Leak Internal Information

**File:** `backend/broker/api/ai.py:118,150,172,204`

All AI error handlers propagate the raw `GeminiError` and `OllamaError` message strings directly to the HTTP response:

```python
except GeminiError as e:
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
```

`GeminiError` messages include the internal Ollama URL (`Cannot connect to ollama daemon at http://127.0.0.1:11434`) and Gemini HTTP response bodies (`Gemini API returned HTTP 429: {full response text}`). These may contain internal infrastructure details or API key-related information.

**Impact:** Internal infrastructure disclosure (internal IP/port, service topology).

**Fix:** Log the full error server-side and return a generic message to the client:
```python
except GeminiError as e:
    logger.error("Gemini generation failed: %s", e)
    raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Please try again.")
```

---

### VULN-15 · Import Template Endpoint Unauthenticated

**File:** `backend/broker/api/quiz.py:505-514`

The Excel import template download endpoint requires no authentication:

```python
@router.get("/import/template")
async def get_import_template(
    service: ExcelImportService = Depends(get_import_service)
):
    """Download the blank Excel template for bulk upload"""
    return FileResponse(path=service.get_template_path(), ...)
```

This is a low-severity issue since the template contains no sensitive data, but it exposes the product feature surface to unauthenticated crawlers and discloses the template format to anyone.

**Impact:** Minor information disclosure of product feature structure.

**Fix:** Add `current_user: CurrentUser = Depends(get_current_user)` to restrict to authenticated users.

---

### VULN-16 · CORS Configuration Accepts Multiple Origins Including Localhost

**File:** `backend/core/config/settings.py:83-86`, `backend/main.py:106-112`

The CORS allowed origins default includes `http://localhost:3000`, which is typically only appropriate for development. If the production `.env` does not explicitly override `ALLOWED_ORIGINS`, the FastAPI app would accept `credentials: true` requests from any localhost origin (useful for local attackers or developer machines). More critically, `allow_credentials=True` with `allow_methods=["*"]` and `allow_headers=["*"]` is a very permissive CORS posture.

**Impact:** Local privilege escalation if a developer's browser is targeted (unlikely but non-zero). More importantly, if the `ALLOWED_ORIGINS` env variable is not set in production, the default allows localhost cross-origin requests.

**Fix:** Verify the production `.env` explicitly sets `ALLOWED_ORIGINS=https://www.swaya.me,https://test.swaya.me` and does not include localhost.

---

## LOW

### VULN-17 · `QuizControl.jsx` Renders Option Text via `dangerouslySetInnerHTML` Without Confirming Sanitization

**File:** `frontend/src/features/quiz/QuizControl.jsx:681`

The "Correct Answer" alert in the host quiz control panel renders the text of the correct option using `dangerouslySetInnerHTML`:

```javascript
<span dangerouslySetInnerHTML={{ __html: currentQuestion[`option_${currentQuestion.correct_answer.toLowerCase()}`] || '' }} />
```

The `option_a`, `option_b`, etc. fields are populated from `answer_service_async.py:452-454` which pulls from the `options` JSON array. Options are sanitized via `sanitize_plain()` when created through the normal flow, but see VULN-05 (Excel import bypasses sanitization). If options contain HTML (possible through the Excel import path), this renders it without escaping.

**Impact:** Conditional XSS in the host control panel if unsanitized options exist (depends on VULN-05 being exploited first).

**Fix:** After fixing VULN-05, this becomes low risk. As defense-in-depth, use a plain text renderer for option labels: `{currentQuestion[`option_${...}`] || ''}` (React's default escaping).

---

### VULN-18 · Participant Session Token Stored in `sessionStorage` and `localStorage`

**File:** `frontend/src/features/audience/AudienceSession.jsx:91-94`, `frontend/src/features/offline-poll/OfflinePollSession.jsx:84`

Audience participant session tokens are stored in `sessionStorage`:
```javascript
sessionStorage.setItem('swaya_participant_session', JSON.stringify({ sessionToken, sessionId, displayName }))
```

Offline poll tokens are stored in `localStorage`:
```javascript
localStorage.setItem(STORAGE_TOKEN_KEY(slug), session_token)
```

These tokens are used to authenticate participant actions (answer submission, session leave). A page-level XSS can exfiltrate them.

**Impact:** If XSS occurs on a participant page, the session token allows an attacker to submit answers or view audience-facing results on the participant's behalf.

**Fix:** The risk is inherent to the anonymous participant flow (no HttpOnly cookie equivalent is available for unauthenticated users). For the offline poll specifically, use `sessionStorage` instead of `localStorage` since offline polls don't require cross-session persistence (the token is sent with each answer anyway).

---

### VULN-19 · Proctoring Biometrics and Event Logging Endpoints Accept Any Session Token Without Validation

**File:** `backend/broker/api/proctoring.py:151-161`, `backend/broker/api/proctoring.py:181-237`

The `POST /proctoring/event` and `POST /proctoring/answer-timing` endpoints accept arbitrary `session_token` values from the request body and log them to the database:

```python
@router.post("/event", response_model=ViolationEventResponse)
async def log_event(body: ViolationEventRequest, ...):
    return await svc.log_violation(body.session_token, body.rule_id, body.event_type, body.metadata, db, redis)
```

There is no check that `body.session_token` is a valid participant token. Junk session tokens get logged. The `answer-timing` endpoint falls back to `accepted=True` if Redis has no data — meaning sending invalid session tokens to timing checks always succeeds.

**Impact:** Database pollution with fake violation events; potential to flood violation logs for a quiz with spurious data to obscure real violations.

**Fix:** Validate the session token against the participants table (or Redis cache) before logging events and return 403 for unrecognized tokens.

---

### VULN-20 · `python-jose` Present in Requirements Despite No Usage

**File:** `backend/requirements.txt:126`

(Covered in VULN-07 above — listed separately here for tracking.)

`python-jose==3.3.0` carries two publicly disclosed CVEs (CVE-2024-33664, CVE-2024-33663) but is not imported anywhere in the application. It should be removed.

**Fix:** `pip uninstall python-jose` and remove from `requirements.txt`.

---

### VULN-21 · `xlsx` Frontend Package Version 0.18.5 Has Known Prototype Pollution Issue

**File:** `frontend/package.json:53`

The `xlsx` package (`SheetJS`) at version `0.18.5` (the last public release before the library moved to a commercial license) has known prototype pollution issues. It is used for client-side spreadsheet parsing and generation (Excel import/export UI).

**Impact:** Prototype pollution could affect client-side code execution in limited scenarios (e.g., a crafted XLSX download manipulating Object.prototype).

**Fix:** Evaluate if the client-side xlsx usage (which appears to be for downloading Excel templates) can be replaced with a server-generated file response, eliminating the dependency. If not, pin to the latest available community fork or `xlsx-js-style` alternative.

---

## INFORMATIONAL

### VULN-22 · `cryptography` Version Mismatch Between requirements.txt and Running Venv

**File:** `backend/requirements.txt:28`

`requirements.txt` pins `cryptography==41.0.7` but the running venv has `47.0.0` installed. While 47.0.0 is *more secure* (fixing issues present in 41.x), the mismatch indicates the requirements.txt is stale and deployment is not reproducible. If a fresh deployment installs from requirements.txt it would install 41.0.7 which has several older CVEs.

**Fix:** Update `cryptography` pin in requirements.txt to `>=43.0.0` (or pin to the currently installed `47.0.0`).

---

### VULN-23 · Metrics Beacon Endpoint Allows Arbitrary Event Type and Properties

**File:** `backend/broker/api/metrics.py:23-45`

The `POST /metrics/event` endpoint stores arbitrary `event_type` strings and `properties` JSON with no validation, for any authenticated or anonymous user:

```python
class EventBeacon(BaseModel):
    event_type: str
    ...
    properties: Optional[Dict[str, Any]] = None
```

There is no max length on `event_type`, no allowlist of valid event types, and `properties` is an unbounded JSON blob. An attacker can store large quantities of data in the `platform_events` table.

**Impact:** Storage exhaustion (DoS against database). Information leakage if the events table is queried in analytics dashboards without proper tenant isolation.

**Fix:** Add a `max_length` constraint to `event_type` and cap `properties` size. Consider an allowlist of valid event types.

---

### VULN-24 · CSRF: SameSite=Strict Cookie Does Protect Against Most CSRF, But GET Endpoints with Side Effects Exist

**File:** `backend/broker/api/quiz.py:718-731`

The `SameSite=Strict` cookie (`access_token`) provides strong CSRF protection for form-submitted cross-site requests. However, `POST /quizzes/sessions/start?quiz_id=N` is a state-changing endpoint triggered by a query parameter (not a body), and is authenticated via cookie. Cross-site `<img>` or `<link>` preload tags cannot trigger POST requests, so this specific example is safe.

One genuine edge case: the Google OAuth callback at `GET /auth/google/callback?code=...` (`backend/broker/api/auth.py:264`) processes auth codes and sets an auth cookie. If `state` parameter CSRF protection is not implemented in the OAuth flow, an attacker can initiate a Google login and link their Google account to a victim's session (OAuth login CSRF / account hijacking).

**Inspection:** The `google_login` endpoint does **not** generate or validate a `state` parameter:
```python
params = {
    "client_id": settings.google.client_id,
    "redirect_uri": f"{settings.app.frontend_url}/auth/google/callback",
    "response_type": "code",
    "scope": "openid email profile",
    "access_type": "offline",
    # No "state" parameter!
}
```

**Impact:** OAuth login CSRF — if a victim is tricked into visiting a malicious page while logged into Swaya.me, the attacker can initiate a Google OAuth flow and potentially link the attacker's Google identity to the victim's account (or log the victim into the attacker's account, allowing the attacker to observe victim activity).

**Fix:** Generate a cryptographically random `state` token, store it in the session/cookie, include it in the Google authorization URL, and validate it in the callback:
```python
import secrets
state = secrets.token_urlsafe(32)
# Store in cookie or Redis keyed by nonce, then:
params["state"] = state
# In callback:
if request.query_params.get("state") != stored_state:
    raise HTTPException(400, "CSRF validation failed")
```

---

### VULN-25 · Tenant Isolation Middleware Does Not Check Cookie-Based JWTs

**File:** `backend/broker/policies/tenant_isolation.py:37-47`

The `tenant_isolation_middleware` only extracts `tenant_id` from the `Authorization` header (Bearer token) and not from the HttpOnly `access_token` cookie:

```python
auth_header = request.headers.get("Authorization")
if auth_header and auth_header.startswith("Bearer "):
    token = auth_header.split(" ")[1]
    ...
    _tenant_id_ctx.set(int(tenant_id))
```

Since the application migrated JWTs to HttpOnly cookies, the `TenantContext` is never populated for cookie-authenticated requests. Any code that calls `get_tenant_context().tenant_id` to scope database queries receives `None` instead of the actual tenant ID. The direct service method calls (which receive `current_user.tenant_id` as a parameter) are not affected, but any middleware-level tenant scoping is silently disabled for cookie-based auth.

**Impact:** If any code path uses `tenant_context.tenant_id` for data isolation (rather than explicit parameter passing), it will see `None` and may perform cross-tenant queries for cookie-authenticated browsers.

**Fix:** Update the middleware to also check the cookie:
```python
token = None
auth_header = request.headers.get("Authorization")
if auth_header and auth_header.startswith("Bearer "):
    token = auth_header.split(" ")[1]
if not token:
    token = request.cookies.get("access_token")
if token:
    ...
```

---

## Summary Table

| ID | Title | Severity | File |
|----|-------|----------|------|
| VULN-01 | Proctoring snapshots served unauthenticated | **Critical** | `backend/main.py:144` |
| VULN-02 | Non-CSPRNG OTP generation | **High** | `exam_service_async.py:158` |
| VULN-03 | No auth on word cloud results endpoint | **High** | `broker/api/quiz.py:1017` |
| VULN-04 | Proctoring lock/unlock missing tenant isolation | **High** | `broker/api/proctoring.py:373` |
| VULN-05 | Excel import bypasses XSS sanitization | **High** | `import_service.py:225-253` |
| VULN-06 | HTML injection in OTP/results emails | **High** | `exam_service_async.py:162` |
| VULN-07 | Vulnerable unused dependency python-jose | **High** | `requirements.txt:126` |
| VULN-08 | User profile in localStorage (XSS-accessible) | **Medium** | `authSlice.js:4,23` |
| VULN-09 | Exam session token in localStorage | **Medium** | `ExamSession.jsx:912` |
| VULN-10 | No rate limiting on AI generation endpoints | **Medium** | `broker/api/ai.py` |
| VULN-11 | No rate limiting on join/submit/OTP endpoints | **Medium** | `broker/api/quiz.py`, `exam.py` |
| VULN-12 | String role comparison in stats_history (brittle) | **Medium** | `stats_history.py:38` |
| VULN-13 | Internal tenant ID leaked in error message | **Medium** | `auth/service_async.py:221` |
| VULN-14 | AI service errors leak internal details | **Medium** | `broker/api/ai.py:118` |
| VULN-15 | Import template download unauthenticated | **Medium** | `broker/api/quiz.py:505` |
| VULN-16 | Overly permissive CORS / localhost default | **Medium** | `settings.py:83` |
| VULN-17 | QuizControl renders option text via dangerouslySetInnerHTML | **Low** | `QuizControl.jsx:681` |
| VULN-18 | Participant session tokens in sessionStorage/localStorage | **Low** | `AudienceSession.jsx:91` |
| VULN-19 | Proctoring event logging accepts unvalidated session tokens | **Low** | `proctoring.py:151` |
| VULN-20 | python-jose unused vulnerable package | **Low** | `requirements.txt:126` |
| VULN-21 | xlsx frontend package prototype pollution risk | **Low** | `package.json:53` |
| VULN-22 | cryptography version mismatch in requirements.txt | **Info** | `requirements.txt:28` |
| VULN-23 | Metrics beacon accepts unbounded arbitrary data | **Info** | `broker/api/metrics.py` |
| VULN-24 | Google OAuth callback missing state CSRF parameter | **Info** | `broker/api/auth.py:264` |
| VULN-25 | Tenant isolation middleware misses cookie-based JWTs | **Info** | `broker/policies/tenant_isolation.py` |
