# Requirements Document: "Exam" Type — Shareable, Self-Paced, Scored Assessment

> **Status:** Approved for implementation
> **Date:** 2026-03-22
> **Requested by:** Vinay

---

## 1. Overview

A new quiz type called **"Exam"** (internal enum: `exam`) is a shareable, self-paced, scored assessment. Unlike "Online Quiz" (which requires a live host to advance questions in real time), an Exam works like a traditional online test:

- Host creates the exam with MCQ questions, correct answers, points, and optional negative marking
- Host sets a time window (start/end date) and optional time limits (exam-level or per-question)
- Host publishes and shares a link — **no host presence required** during participation
- Participants access the link within the window, answer all questions, submit, and immediately see their score
- The system handles all scoring automatically

This type combines the **shareable link + scheduling** mechanics of the existing "Poll" type with the **MCQ scoring** mechanics of the existing "Online Quiz" type.

---

## 2. Positioning Among Existing Types

| Feature | Online Quiz | Online Poll | Poll | **Exam** (new) |
|---|---|---|---|---|
| Host must be online | ✅ Required | ✅ Required | ❌ | ❌ No host needed |
| Shareable link | ❌ | ❌ | ✅ | ✅ |
| Self-paced | ❌ | ❌ | ✅ | ✅ |
| Scored (correct answers) | ✅ | ❌ | ❌ | ✅ |
| Negative marking | ❌ | ❌ | ❌ | ✅ |
| Start / end date | ❌ | ❌ | ✅ | ✅ |
| Exam-level time limit | ❌ | ❌ | ❌ | ✅ |
| Per-question time limit | Stored, not enforced | — | Stored, not enforced | ✅ Enforced |
| Leaderboard visible to | Host + Participants | ❌ | ❌ | **Host only** |
| Resume mid-attempt | — | — | ✅ | ❌ (10-min grace) |

---

## 3. Type Name Summary

| Internal enum | Display name |
|---|---|
| `quiz` | Online Quiz |
| `poll` | Online Poll |
| `offline_poll` | Poll |
| `exam` *(new)* | **Exam** |

---

## 4. User Stories

### Host (Creator)

1. As a host, I can create an Exam with MCQ questions, mark correct answers, assign points per question, and optionally set a negative score for wrong answers.
2. As a host, I can set a **start date/time** and **end date/time** for the exam window (both required to publish).
3. As a host, I can optionally set a **total exam time limit** (e.g., 30 minutes from when a participant starts).
4. As a host, I can optionally set a **per-question time limit** (e.g., 60 seconds; auto-advances on expiry).
5. As a host, I can publish the exam and receive a shareable link (`/e/{slug}`).
6. As a host, I can view a results dashboard: per-participant scores, per-question analytics, and a leaderboard.
7. As a host, I can optionally receive an email summary when the exam window closes.
8. As a host, I can unpublish (disabling the link) and re-publish the exam.

### Participant

1. As a participant, I access the exam link and see a clear status: upcoming, open, or closed.
2. As a participant, I must enter my name (mandatory) before starting.
3. As a participant, I answer one MCQ question at a time.
4. As a participant, I see a countdown per question if a per-question timer is set — the exam auto-advances on expiry.
5. As a participant, I see a global countdown if an exam-level timer is set — the exam auto-submits on expiry.
6. As a participant, I must complete the exam in one sitting (no resume after 10-minute grace period).
7. As a participant, I immediately see my total score and per-question breakdown after submitting.
8. As a participant, I cannot re-take the exam once submitted or after my 10-minute grace period expires.

---

## 5. Functional Requirements

### 5.1 Exam Creation & Settings

QuizBuilder includes **"Exam"** as a new type option alongside Online Quiz, Online Poll, Poll.

When type is "Exam":
- **Question types:** MCQ only (correct answer + points). Word Cloud, Scale, Paragraph, Single Line are not available.
- **Per-question scoring:**
  - `points` (positive integer, default 1) — awarded if answer is correct.
  - `negative_points` (non-negative integer, default 0) — deducted if answer is wrong. If 0, no penalty for wrong answers.
  - Unanswered questions always score 0 — no penalty.
- **Scheduling:** `start_at` and `end_at` are both required to publish.
- **Total time limit** (optional): integer minutes, counted from when participant clicks "Start Exam."
- **Per-question time limit** (optional, per-question): reuses existing `Question.max_time_seconds` field. UI allows a global default that can be overridden per question.
- **Results email** (optional): host email to receive summary after `end_at`.

### 5.2 Publishing

Host clicks **Publish Exam** → system:
1. Validates: has `start_at`, `end_at`, at least 1 question.
2. Generates unique `exam_slug` (URL-safe, 8 chars, like `poll_slug`).
3. Creates a permanent ACTIVE `QuizSession` (reuses existing pattern from offline poll).
4. Sets quiz status to `READY`.
5. Returns shareable URL: `https://www.swaya.me/e/{slug}`.
6. Schedules APScheduler job to email results at `end_at` (if email configured).

Host can **Unpublish** (reverts to DRAFT, slug invalidated) and re-publish.

### 5.3 Participant Flow

```
Access link → Window status check → Name entry → Start Exam → Answer questions (timers) → Submit → Score screen
```

1. **Access link** (`/e/{slug}`):
   - `now < start_at` → "Exam opens on [date/time]"
   - `now > end_at` → "Exam has closed"
   - Participant already completed or abandoned → "You have already attempted this exam"
   - Otherwise → start screen

2. **Start screen**: exam title, description, question count, time limit info, **mandatory name field**. "Start Exam" button.

3. **Taking the exam**:
   - One question per screen with progress bar (Q N of M).
   - **Per-question timer** (if set): countdown bar per question. On expiry → saves current answer (blank if none) → auto-advances. Participant **cannot return** to timed-out questions.
   - **Total timer** (if set): global countdown throughout. On expiry → auto-submits all saved answers.
   - **Navigation rules:**
     - Exam-level time limit only → free **forward and backward** navigation.
     - Per-question time limits active → **forward only** (cannot return to expired questions).
   - Answers saved to server on each navigation step (upsert).

4. **No-resume rule**:
   - Participant must complete in one sitting.
   - If browser is closed, a **10-minute grace period** applies (based on `last_activity_at` timestamp on the server).
   - Within 10 minutes: returning participant can resume where they left off.
   - After 10 minutes: marked as `abandoned`, link shows "You have already attempted this exam."
   - Timer continues running server-side during the grace period (no pausing).

5. **Submit**: Final question → "Submit Exam" confirmation dialog → POST to submit endpoint → server calculates score.

6. **Results screen** (always shown immediately):
   - Total score: "X / Y points (Z%)"
   - Per-question breakdown: participant's answer, correct answer, points earned/lost per question.
   - No leaderboard or rank shown to participant — leaderboard is host-only.

### 5.4 Host Results Dashboard

Accessible at `/quiz/{id}/exam-results` (authenticated host only).

- Exam metadata: title, slug URL, window dates, status (upcoming / open / closed).
- Summary stats: total started, total completed, abandoned count, average score, score distribution chart.
- **Leaderboard**: ranked table — participant name, score, % correct, time taken, completion time.
- Per-question analytics: % correct per question, option distribution bar chart.
- Export (CSV): reuse existing export patterns.
- Visible to host regardless of whether exam is still open.

### 5.5 Time Limit Enforcement

Time limits can be set at either or both levels independently:

**Per-question timer** (`question.max_time_seconds`):
- Countdown bar shown per question.
- On expiry: saves current answer (blank if unanswered) → auto-advances to next question.
- Participant cannot navigate back to a timed-out question.
- Questions without `max_time_seconds` have no individual timer.

**Total exam timer** (`exam_time_limit_seconds` on Quiz model):
- Starts when participant clicks "Start Exam" (server records `participant.started_at`).
- Frontend calculates: remaining = `exam_time_limit_seconds − (now − started_at)`.
- Global countdown shown throughout the exam.
- On expiry: auto-submits all currently saved answers.
- Backend rejects answer saves if `now > started_at + exam_time_limit_seconds`.

**If both are set**: both timers run simultaneously. The per-question timer auto-advances individual questions; the total timer auto-submits everything.

### 5.6 Scoring Calculation

- **Correct answer:** +`question.points`
- **Wrong answer:** −`question.negative_points` (if > 0; otherwise 0)
- **Unanswered:** 0 (no penalty)
- **Final score** = Σ(points for correct) − Σ(negative_points for wrong). Minimum score is clamped to 0.
- **Max possible score** = Σ(question.points) across all questions.
- Score shown immediately after submission.

### 5.7 Abandonment Logic

- Participant starts exam → server records `participant.started_at`.
- Each answer save updates `participant.last_activity_at`.
- On re-access: server checks `now − last_activity_at`.
  - ≤ 10 minutes → participant can resume from where they left off.
  - > 10 minutes → `participant.is_abandoned = True` → access denied.
- Timer continues running server-side during the grace period.

---

## 6. Data Model Changes

### 6.1 New Enum Value
`QuizTypeEnum` adds: `EXAM` (stored as `"exam"` in DB).

### 6.2 Quiz Model — New Fields

| Field | Type | Description |
|---|---|---|
| `exam_slug` | String(64), unique, nullable, indexed | Shareable URL slug |
| `exam_start_at` | DATETIME, nullable | Exam window opens |
| `exam_end_at` | DATETIME, nullable | Exam window closes |
| `exam_time_limit_seconds` | Integer, nullable | Total time per participant (from start click) |
| `exam_session_id` | FK → QuizSession, nullable | Permanent ACTIVE session |
| `exam_results_email` | String(255), nullable | Email for results on close |

### 6.3 Question Model — New Field

| Field | Type | Description |
|---|---|---|
| `negative_points` | Integer, default 0 | Points deducted for a wrong MCQ answer (negative marking) |

> `Question.max_time_seconds` and `Question.points` already exist in the DB — no changes needed.

### 6.4 Participant Model — New Fields

| Field | Type | Description |
|---|---|---|
| `started_at` | DATETIME, nullable | When participant clicked "Start Exam" |
| `last_activity_at` | DATETIME, nullable | Updated on each answer save (used for grace period detection) |
| `is_abandoned` | Boolean, default False | True after grace period expires without submission |

> `completed_at` already exists on Participant.

### 6.5 Answer Model — No Changes
`is_correct` and scoring already work via `answer_service_async.py`. Reused as-is.

### 6.6 Alembic Migration
New file: `backend/persistence/migrations/versions/YYYYMMDD_HHMM_add_exam_type.py`

---

## 7. API Endpoints (New)

New router: `backend/broker/api/exam.py` — registered at `/api/v1`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/quizzes/{id}/publish-exam` | ✅ Host | Publish as exam; generates slug + permanent session |
| `GET` | `/e/{slug}` | ❌ | Exam info (title, status, dates, question count, time limits) |
| `POST` | `/e/{slug}/start` | ❌ | Start exam; returns all questions + session_token; records `started_at` |
| `POST` | `/e/{slug}/answer` | ❌ | Upsert single answer; updates `last_activity_at` |
| `POST` | `/e/{slug}/submit` | ❌ | Submit exam; server scores; returns result |
| `GET` | `/e/{slug}/result` | ❌ | Get own score + breakdown (session_token in body) |
| `GET` | `/quiz/{id}/exam-results` | ✅ Host | Full results: leaderboard, per-question analytics |

---

## 8. Frontend Components

### New Components

| Component | Path | Purpose |
|---|---|---|
| `ExamSession.jsx` | `frontend/src/features/exam/ExamSession.jsx` | Participant-facing exam UI (timers, navigation, submit, score screen) |
| `ExamResults.jsx` | `frontend/src/features/exam/ExamResults.jsx` | Host results dashboard (leaderboard, per-question charts) |

### Modified Components

| Component | Change |
|---|---|
| `QuizBuilder.jsx` | Add "Exam" type option; scheduling fields; time limit fields; negative_points per question |
| `Dashboard.jsx` | Add "Create Exam" button |
| `App.jsx` | Add routes `/e/:slug` (public) and `/quiz/:id/exam-results` (authenticated) |
| `api.js` | Add `examAPI` client methods |

---

## 9. New Backend Service

`backend/features/quiz/exam_service_async.py` — key functions:

| Function | Description |
|---|---|
| `get_exam_info(db, slug)` | Status check (upcoming/open/closed), public metadata |
| `start_exam(db, slug, display_name)` | Create participant, record `started_at`, return all questions |
| `save_answer(db, slug, session_token, ...)` | Upsert answer, update `last_activity_at`, validate time limits |
| `submit_exam(db, slug, session_token)` | Calculate score with negative marking, set `completed_at`, return result |
| `get_my_result(db, slug, session_token)` | Return participant's own score + per-question breakdown |
| `get_exam_results(db, quiz_id, current_user)` | Host-only: full leaderboard + per-question analytics |
| `check_abandonment(db, participant)` | Grace period logic: >10 min inactivity → `is_abandoned = True` |
| `send_results_email(quiz_id)` | APScheduler job at `exam_end_at` |

---

## 10. Locale / i18n

New keys in all 11 locale files under a new `exam` namespace:

- Type label: "Exam"
- Create button: "Create Exam"
- Status messages: upcoming, open, closed, already attempted
- Start screen: name field label, instructions, start button
- Timer labels: per-question countdown, total exam countdown
- Submit confirmation dialog
- Score screen: total points, percentage, per-question breakdown labels
- Results dashboard: leaderboard column headers, analytics labels

---

## 11. Proctoring (Shipped — April 2026)

Proctoring is now implemented as an optional, per-quiz anti-cheating layer. See `Docs/proctoring.md` for the full spec. Key points relevant to the exam type:

### Activation

The host enables proctoring in the exam builder via a toggle. Proctoring is only available for `exam` and `offline_poll` types.

### Exam Builder UX Changes (April 2026)

| Change | Details |
|--------|---------|
| Unified save | A single "Save Settings" button saves both exam metadata and proctoring policy in one `PUT /quizzes/{id}` call — no separate proctoring save button |
| Proctoring panel position | The proctoring settings card appears above the questions list (between metadata form and questions), not below |
| Live exam banner | When `status=ready`, a yellow banner warns that questions are locked and changes take effect immediately |
| Question lock | When exam is live, the questions list is read-only — add/edit/delete/reorder controls are hidden |
| Preset labels | **Light Monitoring** / **Standard Security** / **Maximum Security** (replaces cryptic "Soft/Hard/Paranoid") |
| Escalation summary | Dynamic inline summary: "Participant gets N−1 warning(s), then locked on the Nth violation" |

### Rules Available for Exam Type

All free-tier browser rules (`fullscreen_enforce`, `tab_switch_detect`, `right_click_block`, `copy_paste_block`, `multi_tab_detect`, `bot_signal_detect`, `honeypot_traps`) are available. PRO+ adds `devtools_detect`, `answer_timing`, and `webcam_monitoring`.

### Escalation

- `lock_on_violation_count` — lock after this many cumulative violations (default 3)
- `auto_submit_on_lock` — if true, the participant's answers at lock time are auto-submitted; if false, answers are abandoned on lock unless the participant submitted before being locked

### Webcam (`webcam_monitoring` rule — PRO+)

When enabled, participants must grant camera permission before seeing any exam content. After the browser permission dialog is accepted, the frontend calls `POST /proctoring/session/webcam-granted` to update the database — this is what the Integrity Report reads for the "Webcam Granted" column. The session init call always sets `webcam_granted=false`; only this second call flips it.

### Integrity Report

Available at `/quiz/:id/exam-results` → Integrity tab. Shows per-participant: integrity score, violation count, locked status, webcam_granted, and an expandable event timeline. Admins can manually lock or unlock any session.

---

## 12. Still Out of Scope

- Question order shuffling per participant
- MCQ option order shuffling per participant
- Password-protected exams
- IP-based duplicate detection
- Non-MCQ question types (Word Cloud, Scale, Paragraph, Single Line)
- Certificates / badges on completion
- Partial credit scoring
- Embedding in external pages (iframe)

---

## 13. All Design Decisions

| Decision | Outcome |
|---|---|
| Display name | **"Exam"** |
| Internal enum | `exam` |
| Question types | MCQ only |
| Correct answer | Required per question |
| Negative marking | ✅ Per-question `negative_points` field (default 0) |
| Host presence | ❌ Not required |
| Shareable URL | `/e/{slug}` |
| Start/end date | Both required to publish |
| Exam-level time limit | Optional |
| Per-question time limit | Optional, per question |
| Navigation (exam timer only) | Free forward + backward |
| Navigation (question timer active) | Forward only |
| Resume | 10-minute grace period; after that, permanently abandoned |
| Results visibility | Always shown immediately after submit |
| Leaderboard | Host only — not visible to participants |
| Participant name | Mandatory |
| Score floor | 0 (cannot go negative) |
