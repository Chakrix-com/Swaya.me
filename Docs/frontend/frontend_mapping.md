# Frontend Mapping

## State Management

### Redux Store (`frontend/src/store/store.js`)
| Slice | File | State Shape |
|---|---|---|
| `auth` | `store/authSlice.js` | `{user, token, isAuthenticated, loading, error}` |
| `quiz` | `store/quizSlice.js` | Quiz builder state |
| `session` | `store/sessionSlice.js` | Live session state |
| `userManagement` | `store/slices/userManagementSlice.js` | Admin user list |
| `tenantManagement` | `store/slices/tenantManagementSlice.js` | Tenant list |

### `authSlice.js` Actions
| Action | Effect |
|---|---|
| `loginStart` | Set `loading=true` |
| `loginSuccess(payload)` | Set `user`, `token`, `isAuthenticated=true`; write to `localStorage` |
| `loginFailure(message)` | Set `error` |
| `logout` | Clear all auth state + `localStorage` |
| `refreshUser(user)` | Update `user` in state and `localStorage` |

### Token Storage
- `localStorage.getItem('token')` — JWT Bearer token
- `localStorage.getItem('user')` — JSON-serialized user object
- Auth interceptor in `api.js`: injects `Authorization: Bearer {token}` on every request
- 401/403 response with auth token: clears localStorage, redirects to `/login`

---

## Route → Component → API Mapping

### Public Routes (no auth required)

| Route | Component | API Calls |
|---|---|---|
| `/` | `features/home/Home` | None |
| `/login` | `features/auth/Login` | `authAPI.login()` → POST `/auth/login` |
| `/register` | `features/auth/Register` | `authAPI.register()` → POST `/auth/register` |
| `/verify-email` | `features/auth/VerifyEmail` | `authAPI.verifyEmail()` → POST `/auth/verify-email` |
| `/forgot-password` | `features/auth/ForgotPassword` | `authAPI.forgotPassword()` → POST `/auth/forgot-password` |
| `/reset-password` | `features/auth/ResetPassword` | `authAPI.resetPassword()` → POST `/auth/reset-password` |
| `/auth/google/callback` | `features/auth/GoogleCallback` | `authAPI.googleCallback(code)` → GET `/auth/google/callback` |
| `/join` | `features/audience/AudienceJoin` | `sessionAPI.join()` → POST `/quizzes/sessions/join` |
| `/join/:joinCode` | `features/audience/AudienceJoin` | Same; pre-fills join code |
| `/session/:sessionId` | `features/audience/AudienceSession` | Multiple — see below |
| `/present/:sessionId` | `features/quiz/QuizPresent` | Session state polling |
| `/poll/:slug` | `features/offline-poll/OfflinePollSession` | `offlinePollAPI.*` |
| `/e/:slug` | `features/exam/ExamSession` | `examAPI.*` + `proctoringAPI.*` |
| `/privacy-policy` | `features/home/PrivacyPolicy` | None |
| `/terms-of-service` | `features/home/TermsOfService` | None |
| `/about` | `features/home/About` | None |
| `/help` | `features/home/Help` | None |

### Authenticated Routes (ProLayout)

| Route | Component | API Calls |
|---|---|---|
| `/dashboard` | `features/dashboard/Dashboard` | `quizAPI.list()`, `sessionAPI.listSessions()` |
| `/plans` | `features/dashboard/UserPlans` | `authAPI.getTierPlans()` |
| `/quiz/new` | `features/quiz/QuizBuilder` | `quizAPI.create()`, `questionAPI.*`, `aiAPI.*` |
| `/quiz/:id/edit` | `features/quiz/QuizBuilder` | `quizAPI.get()`, `quizAPI.update()`, `questionAPI.*` |
| `/quiz/:id/control` | `features/quiz/QuizControl` | `sessionAPI.start()`, `sessionAPI.advance()`, `sessionAPI.end()`, etc. |
| `/quiz/:id/history` | `features/quiz/QuizHistory` | `sessionAPI.listSessions()`, `sessionAPI.getResults()` |
| `/quiz/:id/offline-results` | `features/offline-poll/OfflinePollResults` | `offlinePollAPI.getResults()` |
| `/quiz/:id/exam-results` | `features/exam/ExamResults` | `examAPI.getResults()` |
| `/admin/statistics` | `features/admin/Statistics` | `statsAPI.get()`, `statsAPI.getHistory()` |
| `/admin/users` | `features/admin/components/UserManagement` | User management API |
| `/admin/organizations` | `features/admin/OrganizationManagement` | `organizationAPI.*` |
| `/admin/platform-quizzes` | `features/admin/PlatformQuizzes` | `platformQuizAPI.list()` |
| `/admin/tier-management` | `features/admin/TierManagement` | `tierConfigAPI.*` |
| `/admin/feedback` | `features/admin/FeedbackManagement` | `statsAPI.getFeedback()`, `appFeedbackAPI.listAppFeedback()` |

---

## Component → API Call Detail

### `features/auth/Login`
- On form submit: `authAPI.login({email, password})` → dispatch `loginSuccess(response.data)` → navigate to `/dashboard`

### `features/auth/Register`
- On form submit: `authAPI.register({email, password, full_name})` → redirect to verify email page

### `features/audience/AudienceJoin`
- `sessionAPI.join({join_code, display_name})` → stores `session_token`, `session_id` in component state → navigate to `/session/:sessionId`

### `features/audience/AudienceSession`
| API Call | Endpoint | When |
|---|---|---|
| Poll session state | GET `/quizzes/sessions/{id}/state` (NOT DERIVABLE — polling mechanism) | Periodic interval |
| `sessionAPI.submitAnswer()` | POST `/quizzes/sessions/submit-answer` | On MCQ selection |
| `sessionAPI.submitWordCloudAnswer()` | POST `/quizzes/sessions/submit-word-cloud` | On text submit |
| `sessionAPI.getAudienceResults()` | GET `/quizzes/sessions/{id}/audience-results` | Session ends |
| `sessionAPI.getAudienceLeaderboard()` | GET `/quizzes/sessions/{id}/audience-leaderboard` | Leaderboard screen |
| Word cloud: `questionAPI.getWordCloudResults()` | GET `/quizzes/questions/{id}/word-cloud-results` | Word cloud display |

### `features/quiz/QuizBuilder`
| API Call | Endpoint | When |
|---|---|---|
| `quizAPI.get(id)` | GET `/quizzes/{id}` | On load (edit mode) |
| `quizAPI.create(data)` | POST `/quizzes/` | Create mode |
| `quizAPI.update(id, data)` | PUT `/quizzes/{id}` | On change |
| `questionAPI.add(quizId, data)` | POST `/quizzes/{quizId}/questions` | Add question |
| `questionAPI.update(id, data)` | PUT `/quizzes/questions/{id}` | Edit question |
| `questionAPI.delete(id)` | DELETE `/quizzes/questions/{id}` | Delete question |
| `questionAPI.reorder(quizId, orders)` | PUT `/quizzes/{quizId}/questions/reorder` | Drag reorder |
| `questionAPI.uploadImage(...)` | POST `/quizzes/{quizId}/upload-image` | Image upload |
| `quizAPI.publish(id)` | POST `/quizzes/{id}/publish` | Publish button |
| `quizAPI.publishOffline(id)` | POST `/quizzes/{id}/publish-offline` | Offline publish |
| `examAPI.publish(id)` | POST `/quizzes/{id}/publish-exam` | Exam publish |
| `aiAPI.generateQuestions(data)` | POST `/ai/generate/questions` | AI generate |
| `aiAPI.rewrite(data)` | POST `/ai/rewrite` | Rewrite button |
| `quizAPI.listTemplates()` | GET `/quizzes/template-library` | Template library |
| `quizAPI.useTemplate(id)` | POST `/quizzes/template-library/{id}/use` | Use template |

### `features/quiz/QuizControl`
| API Call | Endpoint | When |
|---|---|---|
| `sessionAPI.start(quizId)` | POST `/quizzes/sessions/start` | Start session |
| `sessionAPI.advance(id)` | POST `/quizzes/sessions/{id}/advance` | Next question |
| `sessionAPI.back(id)` | POST `/quizzes/sessions/{id}/back` | Previous question |
| `sessionAPI.end(id)` | POST `/quizzes/sessions/{id}/end` | End session |
| `sessionAPI.toggleLeaderboard(id)` | POST `/quizzes/sessions/{id}/toggle-leaderboard` | Toggle leaderboard |
| `sessionAPI.getResults(id)` | GET `/quizzes/sessions/{id}/results` | View results |
| `sessionAPI.exportSession(id, format)` | GET `/quizzes/sessions/{id}/export` | Export |
| Whiteboard: `sessionAPI.updateWhiteboardState()` | PUT `/quizzes/sessions/{id}/whiteboard-state` | Draw/annotate |

### `features/exam/ExamSession`
| API Call | Endpoint | When |
|---|---|---|
| `examAPI.getInfo(slug)` | GET `/e/{slug}` | Page load |
| `examAPI.start(slug, {display_name})` | POST `/e/{slug}/start` | Start exam |
| `examAPI.saveAnswer(slug, data)` | POST `/e/{slug}/answer` | Each answer |
| `examAPI.submit(slug, session_token)` | POST `/e/{slug}/submit` | Submit |
| `proctoringAPI.getConfig(quizId)` | GET `/proctoring/config/{quizId}` | Before exam starts |
| `proctoringAPI.initSession(body, token)` | POST `/proctoring/session/init` | After config loads |
| `api.post('/proctoring/event', ...)` | POST `/proctoring/event` | Violations |

**Proctoring integration** (`features/proctoring/ProctoringProvider.jsx`):
1. Fetches config via `GET /proctoring/config/{quizId}` with `X-Session-Token` header
2. If `enabled=true`: POSTs to `/proctoring/session/init`
3. All violations: POST `/proctoring/event` with `{session_token, rule_id, event_type, metadata}`
4. Webcam granted: POST `/proctoring/session/webcam-granted`

### `features/proctoring/hooks/useFaceDetector.js`
- Dynamically imports `@mediapipe/tasks-vision`
- Loads `blaze_face_short_range.tflite` from CDN (storage.googleapis.com)
- Calls `reportViolation('webcam_monitoring', 'FACE_NOT_DETECTED', {})` when face absent
- Calls `reportViolation('webcam_monitoring', 'MULTIPLE_FACES_DETECTED', {count})` on >1 face

### `App.jsx`
- On mount when authenticated: `authAPI.getMe()` → dispatch `refreshUser(r.data)`
- `TierBadge` component: `authAPI.getMyLimits()` → display tier + limits tooltip

### `components/GlobalOverlay`
- Houses the global feedback button
- `appFeedbackAPI.submit(data)` → POST `/feedback/app`

### `components/LanguageSwitcher`
- On change: `languageTrackingAPI.updatePreference(data)` or `languageTrackingAPI.logEvent(data)`

---

## Data Flow Patterns

### Authentication Flow
```
Login component
  → authAPI.login(creds)
  → POST /auth/login
  → response.data.access_token stored in localStorage + Redux
  → api.js interceptor attaches token to all subsequent requests
  → App.jsx refreshUser call on mount keeps Redux in sync
```

### Participant Session Flow
```
AudienceJoin
  → sessionAPI.join({join_code, display_name})
  → response: {session_token, session_id, ...}
  → navigate to /session/:sessionId
  → AudienceSession polls state, submits answers using session_token as query param
  → No auth header; identity via session_token only
```

### Proctoring Gate Flow (Exam)
```
ExamSession renders <ProctoringProvider quizId session_token>
  → ProctoringProvider: GET /proctoring/config/{quizId}
  → If enabled: POST /proctoring/session/init
  → ProctoringGate renders:
      1. Warning screen (acknowledgement required)
      2. Webcam gate (if webcam_required)
      3. Identity capture (if require_photo_id)
      4. FullscreenGate (if fullscreen_enforce rule present)
      5. Exam content
  → useProctoringModule registers event listeners (tab switch, copy-paste, etc.)
  → Violations: POST /proctoring/event
  → If locked: ProctoringLockScreen rendered, children hidden
```
