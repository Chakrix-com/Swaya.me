# API Surface

All routes are under prefix `/api/v1`. Documented from source code only.

---

## Auth Routes (`broker/api/auth.py`, prefix: `/auth`)

### POST /auth/register
- **Function**: `register()`
- **Input**: `UserRegisterRequest` — `{email: str, password: str, full_name: str|None}`
- **Output**: `TokenResponse` — `{access_token: "pending_verification", token_type, expires_in: 0, user: UserResponse}`
- **Execution trace**:
  1. `register_user(db, request)` in `core/auth/service_async.py`
  2. Check email uniqueness: `SELECT User WHERE email=?`
  3. Create Tenant (FREE tier, unique slug)
  4. Create User with `hashed_password = hash_password(request.password)` (`core/security/password.py`)
  5. Seed demo Event + Quiz + 2 Questions
  6. Send verification email via `send_verification_email()` (`core/auth/email_service.py`)
  7. Returns `TokenResponse` with `access_token="pending_verification"` (no real token until email verified)
- **Status**: 201

### POST /auth/login
- **Function**: `login()`
- **Input**: `UserLoginRequest` — `{email: str, password: str}`
- **Output**: `TokenResponse` — `{access_token: JWT, token_type: "bearer", expires_in: 86400, user: UserResponse}`
- **Execution trace**:
  1. `login_user(db, request)` in `core/auth/service_async.py`
  2. `SELECT User WHERE email=?`
  3. `verify_password(request.password, user.hashed_password)` (`core/security/password.py`)
  4. Check `is_email_verified` (bypass for `demo@swaya.me`)
  5. `SELECT Tenant WHERE id=user.tenant_id`
  6. Update `last_login_at`, increment `login_count`
  7. `create_access_token({sub, email, tenant_id, tier, role})` (`core/security/jwt.py`)
- **Errors**: 401 (invalid creds), 403 (email not verified)

### GET /auth/me
- **Function**: `get_me()`
- **Auth**: `get_current_user()` required
- **Output**: `UserResponse` — `{id, email, full_name, tenant_id, tenant_name, tier, is_active, role}`
- **Execution trace**: Reads `current_user` from JWT-decoded context; no additional DB query

### POST /auth/verify-email
- **Function**: `verify_email()`
- **Input**: `{token: str}`
- **Output**: `{message: str}`
- **Execution trace**:
  1. `SELECT User WHERE email_verification_token=token`
  2. Set `is_email_verified=True`, clear token
  3. `send_welcome_email(user.email, user.full_name)`

### GET /auth/my-limits
- **Function**: `get_my_limits()`
- **Auth**: Required
- **Output**: `{tier, max_participants, max_questions, max_concurrent_events}`
- **Execution trace**: `TierService(redis).get_tier_config(db, tier_enum)` — Redis-cached (5-min TTL), falls back to `tier_configurations` table

### GET /auth/tier-plans
- **Function**: `get_tier_plans()`
- **Auth**: Required
- **Output**: Array of tier configs for all 4 tiers

### GET /auth/google/login
- **Function**: `google_login()`
- **Output**: Redirect to Google OAuth consent screen
- **Note**: Requires `GOOGLE_CLIENT_ID` to be set; returns 503 otherwise

### GET /auth/google/callback
- **Function**: `google_callback(code: str)`
- **Output**: `TokenResponse`
- **Execution trace**:
  1. Exchange `code` for Google access token via `https://oauth2.googleapis.com/token`
  2. Fetch user profile from `https://www.googleapis.com/oauth2/v3/userinfo`
  3. `oauth_login_or_register(db, "google", profile)` — finds user by `oauth_provider_id`, then by email, then creates new

### POST /auth/forgot-password
- **Function**: `forgot_password()`
- **Input**: `ForgotPasswordRequest` — `{email: str}`
- **Output**: `{message: str}` (always 200; no email enumeration)
- **Execution trace**: Generates `reset_password_token`, sets 1-hour expiry, sends email

### POST /auth/reset-password
- **Function**: `reset_password()`
- **Input**: `ResetPasswordRequest` — `{token: str, new_password: str}`
- **Output**: `{message: str}`
- **Execution trace**: Validates token+expiry, `hash_password(new_password)`, clears token

---

## Quiz Routes (`broker/api/quiz.py`, prefix: `/quizzes`)

### POST /quizzes/
- **Function**: `create_quiz()`
- **Auth**: Required
- **Input**: `QuizCreate` — `{title, description?, quiz_type?, event_id}`
- **Output**: `QuizResponse`
- **Execution trace**: `QuizBuilderServiceAsync.create_quiz(db, request, current_user)` → INSERT into `quizzes` with `tenant_id` from auth context

### GET /quizzes/{quiz_id}
- **Function**: `get_quiz()`
- **Auth**: Required
- **Output**: `QuizResponse` (with questions)
- **Execution trace**: `QuizBuilderServiceAsync.get_quiz(db, quiz_id, current_user)` → `SELECT Quiz WHERE id=? AND tenant_id=?` with eager-loaded questions

### GET /quizzes/
- **Function**: `list_quizzes(event_id?, search?)`
- **Auth**: Required
- **Output**: `List[QuizListResponse]`
- **Execution trace**: `QuizBuilderServiceAsync.list_quizzes(db, current_user, event_id)` → filters by `tenant_id`; optional in-memory `search` filter

### GET /quizzes/folders
- **Function**: `list_folders()`
- **Auth**: Required
- **Output**: `List[FolderResponse]`

### POST /quizzes/folders
- **Function**: `create_folder()`
- **Auth**: Required
- **Input**: `FolderCreateRequest` — `{name, parent_id?}`
- **Output**: `FolderResponse`
- **DB**: INSERT `quiz_folders`; UniqueConstraint on `(tenant_id, parent_id, name)`

### PUT /quizzes/folders/{folder_id}
- **Function**: `update_folder()`
- **Auth**: Required

### DELETE /quizzes/folders/{folder_id}
- **Function**: `delete_folder()`
- **Auth**: Required

### PUT /quizzes/{quiz_id}/folder
- **Function**: `assign_quiz_folder()`
- **Auth**: Required
- **Input**: `FolderAssignRequest` — `{folder_id: int|None}`

### GET /quizzes/templates
### GET /quizzes/template-library
- Both call `QuizBuilderServiceAsync.list_available_templates(db, current_user)`

### POST /quizzes/templates/{template_quiz_id}/use
### POST /quizzes/template-library/{template_quiz_id}/use
- **Function**: `use_template_quiz()` / `use_template_from_library()`
- **Auth**: Required
- **Output**: `QuizResponse` (new DRAFT quiz)
- **Execution trace**: `create_quiz_from_template()` — copies quiz+questions to new tenant-scoped quiz

### PUT /quizzes/{quiz_id}
- **Function**: `update_quiz()`
- **Auth**: Required
- **Input**: `QuizUpdate`
- **Note**: Only allowed when quiz status is DRAFT

### POST /quizzes/{quiz_id}/template
- **Function**: `set_template_status()`
- **Auth**: Required
- **Input**: `TemplateDesignationRequest` — `{is_template: bool, template_scope: "tenant"|"global"}`

### DELETE /quizzes/{quiz_id}
- **Function**: `delete_quiz()`
- **Auth**: Required
- **Note**: Cascades delete to questions via ORM relationship

### POST /quizzes/{quiz_id}/publish
- **Function**: `publish_quiz()`
- **Auth**: Required
- **Output**: `QuizResponse` with status READY
- **Execution trace**: `QuizBuilderServiceAsync.publish_quiz()` → validates question count > 0, sets status=READY

### POST /quizzes/{quiz_id}/publish-offline
- **Function**: `publish_offline_poll()`
- **Auth**: Required
- **Output**: `OfflinePollPublishResponse` — `{poll_slug, poll_url, ...}`

### POST /quizzes/{quiz_id}/unpublish
- **Function**: `unpublish_quiz()`
- **Auth**: Required
- **Output**: `QuizResponse` with status DRAFT

### POST /quizzes/{quiz_id}/duplicate
- **Function**: `duplicate_quiz()`
- **Auth**: Required
- **Output**: New DRAFT `QuizResponse`

### GET /quizzes/{quiz_id}/sessions
- **Function**: `list_quiz_sessions()`
- **Auth**: Required
- **Output**: `SessionListResponse`

### GET /quizzes/import/template
- **Function**: `get_import_template()`
- **Output**: FileResponse — `.xlsx` template

### POST /quizzes/import/export-draft
- **Function**: `export_draft_to_excel()`
- **Input**: JSON body (draft quiz data)
- **Output**: StreamingResponse — `.xlsx`

### POST /quizzes/import/validate
- **Function**: `validate_import_file()`
- **Input**: `UploadFile` — `.xlsx`
- **Output**: Validation results JSON

### POST /quizzes/import/finalize
- **Function**: `finalize_import()`
- **Auth**: Required
- **Input**: Validated import data JSON
- **Output**: `QuizResponse`

### POST /quizzes/{quiz_id}/questions
- **Function**: `add_question()`
- **Auth**: Required
- **Input**: `QuestionCreate` — `{question_type, text, order, options?, correct_answer_index?, points?, max_time_seconds?, ...}`
- **Output**: `QuestionResponse`
- **Execution trace**: `QuestionServiceAsync.add_question()` → checks tier question limit → content filter → INSERT `questions`

### PUT /quizzes/questions/{question_id}
- **Function**: `update_question()`
- **Auth**: Required
- **Input**: `QuestionUpdate`
- **Note**: Only on DRAFT quizzes

### PUT /quizzes/{quiz_id}/questions/reorder
- **Function**: `reorder_questions()`
- **Auth**: Required
- **Input**: `QuestionReorderRequest` — `{question_orders: [{id, order}]}`

### DELETE /quizzes/questions/{question_id}
- **Function**: `delete_question()`
- **Auth**: Required

### POST /quizzes/sessions/start
- **Function**: `start_session(quiz_id: int)`
- **Auth**: Required
- **Input**: `quiz_id` as query param
- **Output**: `SessionResponse`
- **Execution trace**:
  1. `SessionServiceAsync.start_session(db, quiz_id, current_user)`
  2. Check tier concurrent event limit
  3. INSERT `quiz_sessions` with status=CREATED, `current_question_index=-1`
  4. Write audience state to Redis key `session:{session_id}:state`

### POST /quizzes/sessions/join
- **Function**: `join_session()`
- **Input**: `SessionJoinRequest` — `{join_code: str, display_name: str}`
- **Output**: `SessionJoinResponse` — `{session_token, session_id, ...}`
- **Execution trace**:
  1. `SessionServiceAsync.join_session(db, request)`
  2. Lookup Event by `join_code`
  3. Find ACTIVE QuizSession for that Event
  4. Check participant tier limit
  5. INSERT `participants` with `session_token = secrets.token_urlsafe()`
  6. Cache token→participant in Redis: `session_token:{token}` → `{participant_id, session_id, is_active}`
  7. Increment Redis participant count: `session:{id}:participants:count`

### POST /quizzes/sessions/leave
- **Function**: `leave_session(session_token: str)`
- **Input**: `session_token` as query param

### POST /quizzes/sessions/{session_id}/advance
- **Function**: `advance_question()`
- **Auth**: Required
- **Output**: `SessionResponse`
- **Execution trace**: `SessionServiceAsync.advance_question()` → increment `current_question_index`, set question status OPEN, write timing to `session_question_timings`, update Redis audience state cache

### POST /quizzes/sessions/{session_id}/back
- **Function**: `back_question()`
- **Auth**: Required

### POST /quizzes/sessions/{session_id}/toggle-leaderboard
- **Function**: `toggle_leaderboard()`
- **Auth**: Required

### POST /quizzes/sessions/{session_id}/end
- **Function**: `end_session()`
- **Auth**: Required
- **Execution trace**: Sets session status=ENDED, writes final Redis audience state

### GET /quizzes/sessions/{session_id}/whiteboard-state
- **Auth**: Required (host only)

### GET /quizzes/sessions/{session_id}/whiteboard-state/public
- **Input**: `join_code: str` query param (no auth)

### PUT /quizzes/sessions/{session_id}/whiteboard-state
- **Auth**: Required (host only)

### GET /quizzes/sessions/{session_id}/whiteboard-events/public
- **Output**: SSE stream; polls Redis every 0.4s for state changes

### POST /quizzes/sessions/submit-answer
- **Function**: `submit_answer(session_token, request)`
- **Input**: `AnswerSubmitRequest` — `{session_id, question_id, selected_option_index}`; `session_token` as query param
- **Output**: `AnswerSubmitResponse`
- **Execution trace**:
  1. `AnswerServiceAsync.submit_answer(db, session_token, request)`
  2. Lookup participant via Redis (fast path) or DB fallback
  3. Validate question status is OPEN
  4. Check no duplicate answer: `SELECT Answer WHERE participant_id=? AND question_id=?`
  5. Determine `is_correct` (if MCQ and `correct_answer_index` set)
  6. INSERT `answers`
  7. Update Redis answer distribution counter

### POST /quizzes/sessions/submit-word-cloud
- **Function**: `submit_word_cloud_answer()`
- **Input**: `WordCloudAnswerSubmitRequest` — `{session_id, question_id, text_answer}`
- **Execution trace**: Content filter applied; word cloud type allows multiple submissions

### GET /quizzes/sessions/{session_id}/leaderboard
- **Auth**: Required (host only via `_assert_host_session_access`)

### POST /quizzes/sessions/feedback
- Participant feedback; `session_token` as query param

### POST /quizzes/feedback
- Authenticated user feedback

### GET /quizzes/questions/{question_id}/word-cloud-results
- **Input**: `session_id` query param

### GET /quizzes/sessions/{session_id}/export
- **Auth**: Required
- **Input**: `format` query param — `pdf|docx|pptx|xlsx`
- **Output**: StreamingResponse binary file

### GET /quizzes/sessions/{session_id}/results
- **Auth**: Required
- **Output**: `SessionResultsResponse`

### GET /quizzes/sessions/{session_id}/audience-results
- **Input**: `session_token` query param
- **Output**: `SessionResultsResponse` (filtered — no question-level correct answers, no text responses)

### GET /quizzes/sessions/{session_id}/audience-leaderboard
- **Input**: `session_token` query param

---

## Exam Routes (`broker/api/exam.py`)

### GET /e/{slug}
- **Function**: `get_exam_info()`
- **Output**: `ExamInfoResponse` — `{status: upcoming|open|closed, title, question_count, time_limit_seconds, starts_at, ends_at}`

### POST /e/{slug}/start
- **Function**: `start_exam()`
- **Input**: `ExamStartRequest` — `{display_name: str}`
- **Output**: `ExamStartResponse` — `{session_token, questions: [...], time_limit_seconds}`

### POST /e/{slug}/answer
- **Function**: `save_answer()`
- **Input**: `ExamAnswerRequest` — `{session_token, question_id, selected_option_index}`

### POST /e/{slug}/submit
- **Function**: `submit_exam()`
- **Input**: `ExamSubmitRequest` — `{session_token}`
- **Output**: `ExamSubmitResponse` — `{score, total, breakdown}`

### POST /e/{slug}/result
- **Function**: `get_my_result()`
- **Input**: `ExamSubmitRequest` — `{session_token}`

### GET /quiz/{quiz_id}/exam-results
- **Auth**: Required (host)
- **Output**: `ExamResultsResponse`

### POST /quizzes/{quiz_id}/publish-exam
- **Auth**: Required

### POST /quizzes/{quiz_id}/unpublish-exam
- **Auth**: Required

---

## Offline Poll Routes (`broker/api/offline_poll.py`, prefix: `/offline-poll`)

### GET /offline-poll/{slug}
### POST /offline-poll/{slug}/join
- **Input**: `{display_name?, session_token?}` — `session_token` for resume

### POST /offline-poll/{slug}/answer
### POST /offline-poll/{slug}/complete
### GET /offline-poll/{slug}/results
- **Auth**: Required (host only)

---

## Proctoring Routes (`broker/api/proctoring.py`, prefix: `/proctoring`)

### POST /proctoring/session/init
- **Auth**: Session token via `X-Session-Token` header
- **Input**: `SessionInitRequest` — `{quiz_id, browser_fingerprint, webcam_granted}`
- **Output**: `SessionInitResponse`
- **Execution trace**:
  1. Resolve quiz and participant
  2. `ProctoringContextResolver.resolve()` — merges platform/tenant/quiz rules
  3. INSERT `proctoring_sessions` (idempotent)
  4. Write Redis session: `proctor:session:{token}` → `{violation_count, is_locked, ...}`

### POST /proctoring/session/webcam-granted
- **Auth**: `X-Session-Token` header

### GET /proctoring/config/{quiz_id}
- **Auth**: `X-Session-Token` optional
- **Output**: `ResolvedRuleSet` + optional `honeypot_config`
- **Execution trace**: `svc.get_config()` → `ProctoringContextResolver.resolve()` → Redis-cached 1h

### POST /proctoring/event
- **Input**: `ViolationEventRequest` — `{session_token, rule_id, event_type, metadata}`
- **Output**: `ViolationEventResponse` — `{logged, is_locked, violations_remaining, silent}`
- **Execution trace**: `svc.log_violation()` → Redis session lookup → INSERT `proctoring_events` → escalation check → optional lock

### GET/POST /proctoring/honeypot
- Silent; always returns 200; validates honeypot trap hits in background

### POST /proctoring/answer-timing
### POST /proctoring/biometrics
### POST /proctoring/snapshot
- Upload webcam snapshot to `/uploads/proctoring/{quiz_id}/{participant_id}/`

### GET /proctoring/report/{quiz_id}
- **Auth**: Required (host, tenant-scoped)

### POST /proctoring/lock/{session_token}
### POST /proctoring/unlock/{session_token}
- **Auth**: Required (admin)

### GET /proctoring/rules
- **Auth**: Required; filtered by tenant tier

### GET /proctoring/admin/rules
### PUT /proctoring/admin/rules/{rule_id}
### GET /proctoring/admin/tenant-policy/{tenant_id}
### PUT /proctoring/admin/tenant-policy/{tenant_id}
- **Auth**: Required (admin/super_admin)

---

## AI Routes (`broker/api/ai.py`, prefix: `/ai`)

### GET /ai/models
- **Auth**: `require_admin`
- **Output**: `{models: [str], default_model: str}`
- **Execution trace**: `list_available_models()` → `GET http://127.0.0.1:11434/api/tags`

### POST /ai/generate/questions
- **Auth**: `require_admin`
- **Input**: `{topic, count (1-10), language, model?}`
- **Output**: `{questions: [{text, options, correct_answer_index}], model}`
- **Execution trace**: `generate_questions()` → httpx POST to Ollama `/api/generate` → parse JSON response

### POST /ai/generate/options
- **Auth**: `require_admin`
- **Input**: `{question, correct_answer, count (1-5), model?}`

### POST /ai/generate/poll-prompt
- **Auth**: `require_admin`

### POST /ai/rewrite
- **Auth**: Any authenticated user
- **Input**: `{text, context, language, model?}`

---

## Admin Routes

### Stats (`broker/api/stats.py`, prefix: `/admin`)
- `GET /admin/stats` — current platform/tenant stats
- `POST /admin/stats/capture?granularity=HOURLY|DAILY`

### Stats History (`broker/api/stats_history.py`)
- `GET /admin/stats/history?granularity=&scope=&tenant_id=&start_date=&end_date=`

### Organization Management (`broker/api/organization_management.py`, prefix: `/admin`)
- `GET /admin/organizations`
- `POST /admin/organizations`
- `GET /admin/organizations/{id}`
- `PATCH /admin/organizations/{id}`
- `GET /admin/organizations/{id}/admins`
- `POST /admin/admin-users`
- `PATCH /admin/admin-users/{admin_id}/quota`
- `GET /admin/admin-users/{admin_id}/usage`

### User Management (`broker/api/user_management.py`)
- Tenant-scoped user CRUD

### Tier Management (`broker/api/tier_management.py`, prefix: `/admin`)
- `GET /admin/tier-configs`
- `PUT /admin/tier-configs/{tier}`

### Quiz Admin (`broker/api/quiz_admin.py`, prefix: `/admin`)
- `GET /admin/quizzes` — platform-wide quiz listing (super_admin only)

### Language Tracking (`broker/api/language_tracking.py`)
- `POST /user/language-preference` — update authenticated user's language
- `POST /language-tracking/event` — log anonymous language change
- `GET /admin/language-stats`
- `GET /admin/language-stats/export`

### App Feedback
- `POST /feedback/app` — submit global app feedback (anonymous or authenticated)
- `GET /admin/app-feedback` — list (admin only)

### OG (`broker/api/og.py`)
- Open Graph image generation for social sharing
