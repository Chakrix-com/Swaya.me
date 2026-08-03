# Critical Flows

---

## Flow 1: User Login

### Step-by-step

**1. User submits credentials**
- Component: `features/auth/Login`
- API call: `authAPI.login({email, password})` (`frontend/src/services/api.js:api.post('/auth/login', data)`)

**2. Request reaches router**
- Route: `POST /api/v1/auth/login`
- Handler: `login()` in `broker/api/auth.py`
- Dependency: `get_async_db` — yields `AsyncSession`

**3. Auth service validates**
- Function: `login_user(db, request)` in `core/auth/service_async.py`
- DB: `SELECT users WHERE email = request.email`
- `verify_password(request.password, user.hashed_password)` — passlib bcrypt verify (`core/security/password.py`)
- If email not verified (and not `demo@swaya.me`): raise `EmailNotVerifiedError` → 403

**4. Tenant loaded**
- DB: `SELECT tenants WHERE id = user.tenant_id`
- If tenant inactive: raise `TenantNotFoundError` → 401

**5. Login tracking updated**
- DB: `UPDATE users SET last_login_at=now(), login_count+=1`
- `await db.commit()`

**6. JWT issued**
- `create_access_token({sub: str(user.id), email, tenant_id, tier, role})` in `core/security/jwt.py`
- Algorithm: HS256; expiry: 24h from `settings.jwt.expiration_hours`

**7. Response**
- `TokenResponse(access_token, token_type="bearer", expires_in=86400, user=UserResponse)`

**8. Frontend stores token**
- `authSlice.loginSuccess(response.data)` — stores token in `localStorage['token']` and `localStorage['user']`
- `isAuthenticated` set to True → App.jsx routes to `/dashboard`

**9. Subsequent requests**
- `api.js` interceptor: `config.headers.Authorization = 'Bearer {token}'`

---

## Flow 2: Host Creates and Launches a Quiz Session

### Step 2a: Create Quiz

**1.** `QuizBuilder` (`features/quiz/QuizBuilder`) mounts; host clicks "New Quiz"
**2.** `quizAPI.create({title, quiz_type: "quiz", event_id})` → `POST /api/v1/quizzes/`
**3.** Handler: `create_quiz()` in `broker/api/quiz.py`; auth via `get_current_user()`
**4.** Service: `QuizBuilderServiceAsync.create_quiz(db, request, current_user)` in `features/quiz/quiz_service_async.py`
**5.** DB: `INSERT INTO quizzes (tenant_id, event_id, title, status="draft", ...)`
**6.** Returns `QuizResponse`

### Step 2b: Add Questions

**1.** Host adds question in QuizBuilder UI
**2.** `questionAPI.add(quizId, {text, question_type, options, correct_answer_index, order})` → `POST /api/v1/quizzes/{quizId}/questions`
**3.** Handler: `add_question()` in `broker/api/quiz.py`
**4.** Service: `QuestionServiceAsync.add_question(db, quiz_id, request, current_user)` in `features/quiz/question_service_async.py`
**5.** Check: `quiz.tenant_id == current_user.tenant_id` and `quiz.status == DRAFT`
**6.** Tier check: `tier_service.check_question_limit(db, tenant_id, quiz_id, tier, current_count)`
**7.** Content filter applied
**8.** DB: `INSERT INTO questions (...)`

### Step 2c: Publish Quiz

**1.** Host clicks "Publish"
**2.** `quizAPI.publish(quizId)` → `POST /api/v1/quizzes/{quizId}/publish`
**3.** Service: `QuizBuilderServiceAsync.publish_quiz()` — validates at least 1 question, sets `status=READY`
**4.** DB: `UPDATE quizzes SET status="ready"`

### Step 2d: Start Live Session

**1.** Host navigates to QuizControl, clicks "Start Session"
**2.** `sessionAPI.start(quizId)` → `POST /api/v1/quizzes/sessions/start?quiz_id={quizId}`
**3.** Handler: `start_session()` in `broker/api/quiz.py`
**4.** Service: `SessionServiceAsync.start_session(db, quiz_id, current_user)` in `features/quiz/session_service_async.py`
**5.** Tier check: `tier_service.check_concurrent_events_limit(db, tenant_id, tier)` — counts CREATED+ACTIVE sessions
**6.** DB: `INSERT INTO quiz_sessions (quiz_id, tenant_id, status="created", current_question_index=-1)`
**7.** Write initial audience state to Redis: `session:{id}:state`
**8.** Returns `SessionResponse` including `session_id`

**9.** Host advances to first question: `sessionAPI.advance(session_id)` → `POST /api/v1/quizzes/sessions/{id}/advance`
**10.** Service: `advance_question()` → increments `current_question_index` to 0, sets `current_question_status=OPEN`
**11.** DB: `INSERT INTO session_question_timings (session_id, question_id, question_index, opened_at=now())`
**12.** Redis: Overwrite audience state cache with new question data
**13.** Status set to `ACTIVE` if was `CREATED`

---

## Flow 3: Audience Member Joins and Submits an Answer

### Step 3a: Join Session

**1.** User navigates to `/join` or `/join/{joinCode}` → `AudienceJoin` component
**2.** `sessionAPI.join({join_code, display_name})` → `POST /api/v1/quizzes/sessions/join`
**3.** Handler: `join_session()` in `broker/api/quiz.py` (no auth required)
**4.** Service: `SessionServiceAsync.join_session(db, request)` in `features/quiz/session_service_async.py`
**5.** DB: `SELECT events WHERE join_code = request.join_code`
**6.** DB: Find ACTIVE `QuizSession` for that event
**7.** Tier check: `tier_service.check_participant_limit(db, tenant_id, session_id, tier)` — checks Redis counter
**8.** DB: `INSERT INTO participants (session_id, display_name, session_token=secrets.token_urlsafe())`
**9.** Redis: `SET session_token:{token} → {participant_id, session_id, is_active: true}` (fast-path cache)
**10.** Redis: `INCR session:{session_id}:participants:count`
**11.** Returns `SessionJoinResponse` — includes `session_token`, `session_id`
**12.** Frontend navigates to `/session/{sessionId}`, stores `session_token`

### Step 3b: Submit MCQ Answer

**1.** Audience sees question, selects option
**2.** `sessionAPI.submitAnswer(session_token, {session_id, question_id, selected_option_index})` → `POST /api/v1/quizzes/sessions/submit-answer?session_token={token}`
**3.** Handler: `submit_answer()` in `broker/api/quiz.py`
**4.** Service: `AnswerServiceAsync.submit_answer(db, session_token, request)` in `features/quiz/answer_service_async.py`
**5.** Participant lookup: Redis `GET session_token:{token}` (fast path) — returns `_CachedParticipant` stub
**6.** If cache miss: `SELECT participants WHERE session_token = token`
**7.** Validate `participant.is_active` — 403 if not (session restarted)
**8.** Check duplicate: `SELECT answers WHERE participant_id=? AND question_id=?` — raises `DuplicateAnswerError` if found
**9.** Validate question open: check session state from Redis or DB
**10.** Determine `is_correct = (selected_option_index == question.correct_answer_index)` if MCQ and answer exists
**11.** DB: `INSERT INTO answers (session_id, participant_id, question_id, selected_option_index, is_correct)`
**12.** Redis: Update answer distribution counter for the question
**13.** Returns `AnswerSubmitResponse`

---

## Flow 4: Host Ends Session and Exports Results

### Step 4a: End Session

**1.** Host clicks "End Session" in `QuizControl`
**2.** `sessionAPI.end(sessionId)` → `POST /api/v1/quizzes/sessions/{id}/end`
**3.** Service: `SessionServiceAsync.end_session(db, session_id, current_user)` in `features/quiz/session_service_async.py`
**4.** Verify `session.tenant_id == current_user.tenant_id`
**5.** DB: `UPDATE quiz_sessions SET status="ended"`
**6.** Redis: Update audience state cache with `status="ended"`
**7.** Returns `SessionResponse`

### Step 4b: View Results

**1.** `sessionAPI.getResults(sessionId)` → `GET /api/v1/quizzes/sessions/{id}/results`
**2.** Handler: `get_session_results()` in `broker/api/quiz.py`
**3.** `_assert_host_session_access(db, session_id, current_user)` — SELECT QuizSession.id WHERE id=? AND tenant_id=?
**4.** `session_service.reconcile_timed_question_state(db, session_id)` — closes any open question timings
**5.** `AnswerServiceAsync.get_session_results(db, session_id, participant_token=None)` in `features/quiz/answer_service_async.py`
**6.** DB: Aggregate answers per question, calculate correct counts, scoring
**7.** Returns `SessionResultsResponse` — includes per-question results, participant scores

### Step 4c: Export Results

**1.** Host selects format (PDF/DOCX/PPTX/XLSX) and clicks export
**2.** `sessionAPI.exportSession(sessionId, format)` → `GET /api/v1/quizzes/sessions/{id}/export?format=pdf`
**3.** Handler: `export_session_results()` in `broker/api/quiz.py`
**4.** `ExportService().generate(session_id, format, db, tenant_id, answer_service)` in `features/quiz/export_service.py`
**5.** Loads session results, generates file:
   - `pdf`: reportlab
   - `docx`: python-docx
   - `pptx`: python-pptx
   - `xlsx`: openpyxl
   - Word cloud questions: `wordcloud` + `Pillow` renders image embedded in doc
**6.** Returns `StreamingResponse` with binary file + `Content-Disposition: attachment`

---

## Flow 5: Exam Proctoring Flow

### Step 5a: Participant Accesses Exam

**1.** Participant navigates to `/e/{slug}` → `ExamSession` component
**2.** `examAPI.getInfo(slug)` → `GET /api/v1/e/{slug}`
**3.** Service: `exam_service_async.get_exam_info(db, slug)` — checks `exam_start_at`/`exam_end_at` → returns status (`upcoming|open|closed`)
**4.** If `closed` or `upcoming`: StatusScreen shown, flow stops

### Step 5b: Participant Starts Exam

**1.** Participant enters display name, clicks Start
**2.** `examAPI.start(slug, {display_name})` → `POST /api/v1/e/{slug}/start`
**3.** Service: `exam_service_async.start_exam(db, slug, display_name)` in `features/quiz/exam_service_async.py`
**4.** DB: `INSERT INTO participants (session_id=exam_session_id, display_name, session_token=secrets.token_urlsafe())`
**5.** Returns `ExamStartResponse` — `{session_token, questions: [...all questions...], time_limit_seconds}`
**6.** Frontend stores `session_token`

### Step 5c: Proctoring Configuration Loaded

**1.** `<ProctoringProvider quizId={quizId} sessionToken={token}>` mounts immediately
**2.** `GET /api/v1/proctoring/config/{quizId}` (with `X-Session-Token` header)
**3.** Backend: `svc.get_config()` → `ProctoringContextResolver.resolve()` in `features/proctoring/context_resolver.py`
**4.** Resolver checks: `quiz.proctoring_policy.enabled == True` → if not, returns `{enabled: false}`
**5.** If enabled: loads `platform_proctoring_rules` (active only), loads `tenant_proctoring_policies`, merges with quiz-level `proctoring_policy.rules`
**6.** Cached in Redis: `proctor:rules:{quiz_id}:{hash}` — 1h TTL
**7.** Returns `ResolvedRuleSet` — `{enabled, rules: [{rule_id, severity, config}], escalation, webcam_required}`
**8.** If `enabled`: POST `/api/v1/proctoring/session/init` with `{quiz_id, browser_fingerprint, webcam_granted: false}`
**9.** Backend: `svc.init_session()` → INSERT `proctoring_sessions` (idempotent); write Redis `proctor:session:{token}`
**10.** **CRITICAL**: `ProctoringProvider` blocks exam content behind spinner until config loaded (`if (!ruleSet) return spinner`)

### Step 5d: Proctoring Gate Execution

**Component**: `ProctoringGate` in `features/proctoring/ProctoringGate.jsx`

**Gate sequence (in order)**:
1. **Warning screen**: If `resolvedRules.length > 0` and not yet acknowledged → show `ProctoringWarningScreen`
   - Lists all active rules, lock threshold, auto-submit policy
   - Participant must check checkbox, then click Acknowledge
   - Acknowledge button synchronously calls `document.documentElement.requestFullscreen()` if `fullscreen_enforce` rule present

2. **Webcam gate**: If `webcam_required` → `useWebcamGate` hook requests `getUserMedia({video: true})`
   - Denied → `WebcamDeniedScreen` shown; logs `WEBCAM_PERMISSION_DENIED` violation
   - Granted → `webcam-granted` POST to backend

3. **Identity capture**: `ExamIdentityCapture` shown if `webcam_monitoring.config.require_photo_id`
   - Captures photo from webcam stream

4. **Fullscreen gate** (`FullscreenGate`): if `fullscreen_enforce` rule present
   - Monitors `document.fullscreenElement`
   - If exited during exam: shows hard block screen with Retry button
   - **Exam content NEVER shown unless `document.fullscreenElement` is set**

### Step 5e: Active Monitoring During Exam

Hooks activated after gate passes:
- `useProctoringModule`: event listeners for tab visibility change (`tab_switch_detect`), copy-paste (`copy_paste_block`), right-click (`right_click_block`), DevTools open (`devtools_detect`), multiple tabs (`multi_tab_detect`)
- `useWebcamMonitor`: periodic webcam activity check; reports `WEBCAM_STREAM_ENDED` on stream end
- `useFaceDetector`: MediaPipe BlazeFace via dynamic import from CDN; runs on video frames via `requestAnimationFrame`
  - No face for `face_absent_warn_sec` → reports `FACE_NOT_DETECTED` to `/proctoring/event`
  - Multiple faces → reports `MULTIPLE_FACES_DETECTED`

### Step 5f: Violation Processing

**1.** Frontend: `reportViolation(rule_id, event_type, metadata)` in `ProctoringProvider`
**2.** POST `/api/v1/proctoring/event` with `{session_token, rule_id, event_type, metadata}`
**3.** Backend: `svc.log_violation()` in `features/proctoring/proctoring_service_async.py`
**4.** Redis: `GET proctor:session:{token}` — returns session data
**5.** DB: `INSERT INTO proctoring_events`
**6.** Escalation check (`_check_escalation()`):
   - Immediate-lock events: `MULTI_TAB_DETECTED`, `HONEYPOT_OPTION_CLICKED`, etc. → `lock_session()` immediately
   - Otherwise: increment `violation_count` in Redis and DB
   - If `violation_count >= lock_threshold` (default 3): call `lock_session()`
**7.** Lock: Redis `proctor:session:{token}.is_locked = true`; DB `UPDATE proctoring_sessions SET is_locked=true, locked_at=now()`; INSERT `SESSION_LOCKED` event
**8.** Response: `{logged, is_locked, violations_remaining, silent}`
**9.** Frontend: If `is_locked=true` → `ProctoringLockScreen` rendered; exam content hidden
**10.** Frontend: If not locked and not silent → show `ProctoringOverlay` with violations remaining count

### Step 5g: Exam Submission

**1.** Participant clicks Submit (or auto-submitted on lock if `auto_submit_on_lock=true`)
**2.** `examAPI.submit(slug, session_token)` → `POST /api/v1/e/{slug}/submit`
**3.** Service: `exam_service_async.submit_exam(db, slug, session_token)`
**4.** DB: Load all answers for participant → score each MCQ answer
**5.** DB: `UPDATE participants SET completed_at=now()`
**6.** Returns `ExamSubmitResponse` — `{score, total, correct_count, per_question_breakdown}`

---

## Flow 6: Coding Challenge — Invite through Grading

### Step 6a: Host Invites a Candidate

**1.** Host adds a `coding_challenge`-type question (starter repo URL, test command) to a `coding_challenge` quiz, publishes it.
**2.** Host invites candidates: `codingChallengeAPI.invite(quizId, {candidate_emails})` → `POST /api/v1/quizzes/{quizId}/coding-challenge/invite`
**3.** Handler: `invite_candidates()` in `broker/api/coding_challenge.py`
**4.** Per email: `svc.create_invite_token(quiz_id, question_id, email)` — a signed JWT (7-day validity, embeds `quiz_id`, `question_id`, `candidate_email`, `attempt_number`, `jti`), no server-side session created for it
**5.** DB: upsert `coding_challenge_invites` row (tracks "who was invited," since no `CodeWorkspace` exists until `/start`)
**6.** Emails the invite link (best-effort — a failed send still returns the link so the host can share it manually)

### Step 6b: Candidate Verifies and Starts

**1.** Candidate opens `/c/{token}` → `CodingChallengeSession`
**2.** `codingChallengeAPI.getInfo(token)` → `GET /coding-challenge/{token}` — decodes the JWT, fetches the starter repo's README as the problem statement
**3.** Candidate clicks "Send code" → `POST /coding-challenge/{token}/request-otp` — 6-digit OTP stored in Redis (10-min TTL, max 3 requests/10min)
**4.** Candidate enters OTP → `codingChallengeAPI.start(token, ideType, otp)` → `POST /coding-challenge/{token}/start`
**5.** Handler: `start_coding_challenge()` in `broker/api/coding_challenge.py`. Verifies OTP (single-use, deleted from Redis on success), checks the concurrency cap (`MAX_CONCURRENT_WORKSPACES`), inserts a `CodeWorkspace` row as `status=provisioning`
**6.** **Does not provision inline.** `svc.schedule_provision_job(workspace.id)` schedules `provision_workspace_job` (APScheduler `DateTrigger`, fires almost immediately) and the endpoint returns `{status: "provisioning", ...}` right away — this is what lets a slow/contended provision on the shared Coder sandbox never time out the candidate's request (the old synchronous version could take 70-150s+ under concurrency, which used to race nginx's `proxy_read_timeout`)

### Step 6c: Background Provisioning

**1.** `provision_workspace_job(workspace_id)` in `features/coding_challenge/coding_challenge_service_async.py` runs in its own DB session
**2.** `coder_client.create_workspace()` — `coder create <name> -t code-server-multi --parameter git_repo_url=<url> -y`, gated by a `CODER_MAX_PARALLEL_PROVISIONS` semaphore (serializes concurrent `coder create` calls against the shared sandbox, since that contention is what caused provisioning-time variance under concurrency)
**3.** `coder_client.wait_for_app_ready()` — polls `coder ssh <ws> -- curl localhost:13337` until code-server responds (or times out — logged as a warning, not fatal)
**4.** `coder_client.mint_session_url()` — mints an API token scoped to just this workspace
**5.** On success: `status=active`, `workspace_url` set, `created_at` reset to now (the candidate's time budget anchors to when the workspace actually became usable, not to when the row was inserted) — schedules the hard-lifetime-cap reaper job (`schedule_lifetime_cap_job`)
**6.** On a `create_workspace` failure: `status=provision_failed` — no cleanup needed, a retried `/start` reuses this row in place

### Step 6d: Candidate Polls for Readiness, Opens Workspace

**1.** `CodingChallengeSession` polls `codingChallengeAPI.getStatus(token)` → `GET /coding-challenge/{token}/status` every few seconds
**2.** Handler reads the `CodeWorkspace` row only — never calls out to Coder itself
**3.** `workspace_url` present → frontend opens it in a new tab, starts the countdown timer, phase → `started`
**4.** `status: "provision_failed"` → frontend shows an error, sends the candidate back to the OTP step (a fresh OTP is required for `/start` to succeed again)

### Step 6e: Candidate Submits

**1.** Candidate clicks Submit → `codingChallengeAPI.submit(token)` → `POST /coding-challenge/{token}/submit`
**2.** Handler: the one synchronous, load-bearing step is `revoke_token()` — immediately cuts off further IDE access
**3.** DB: `status=submitted` on the workspace, `INSERT code_submissions (status=queued)`
**4.** Schedules `run_grading_job(submission_id)` (same `DateTrigger`-fires-immediately pattern as provisioning) and returns `{status: "queued"}`

### Step 6f: Background Grading

**1.** `run_grading_job()` in `features/coding_challenge/grading_service_async.py`: runs the question's `test_command` inside the workspace, harvests `test_output`/`passed_count`/`total_count`, `git log -p` as `code_timeline`, and the AI chat transcript
**2.** `_run_ai_scoring()` — a separate AI pass assesses code quality/approach against the (possibly host-overridden) `grading_weights`; combined into `score_breakdown`/`ai_score`/`ai_verdict`
**3.** Tears down the Coder workspace (`_cleanup()`)
**4.** `status=graded` (or `partial_failed` if only the AI-assessment step failed, `failed` if the harvest itself failed — never the candidate's fault, never shown as a failure to them)
**5.** Candidate's `/status` poll now returns the terminal status — response detail (`ai_score`/`ai_verdict` vs. just a positive/negative signal vs. nothing) is gated by the question's `result_visibility` setting

### Step 6g: Host Reviews

**1.** Host opens the review screen → `codingChallengeAPI.getReview(questionId)` → `GET /quiz-builder/questions/{id}/coding-challenge-review`
**2.** Merges `coding_challenge_invites` + `code_workspaces` + `code_submissions` (three independent records per candidate) into one row per candidate email
**3.** A `partial_failed` submission can be regraded from already-persisted data: `POST .../submissions/{id}/regrade` — re-runs only the AI-assessment step, no workspace needed
