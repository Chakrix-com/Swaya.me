# Feature List — Swaya.me (Current)

## Overview

Swaya.me is a live audience engagement platform. Hosts create and run interactive sessions; participants join anonymously via a join code. This document reflects all shipped features as of April 2026.

---

## Quiz Modes

| Mode | Description |
|------|-------------|
| **Quiz** | Live, host-controlled quiz with scoring, per-question timers, leaderboard, and real-time participation |
| **Poll** | Live, host-controlled poll — no scoring, no leaderboard |
| **Exam** | Self-paced async exam with timed submission and individual results |
| **Offline Poll** | Async poll accessible via public URL/QR — no live host required |

---

## Question Types

| Type | Available Modes | Description |
|------|----------------|-------------|
| `mcq` | All | Multiple choice, one correct answer; supports images on question and each option |
| `word_cloud` | Quiz, Poll | Open text response rendered as a live word cloud; profanity-filtered |
| `one_word` | Quiz, Poll | Single-word text answer; multi-word submissions rejected |
| `single_line` | Quiz, Poll, Exam | Short free-text response (one line) |
| `paragraph` | Quiz, Poll, Exam | Long free-text response |
| `scale` | Quiz, Poll | Numeric scale response (e.g. 1–5 rating) |

---

## Quiz Builder

| Feature | Description |
|---------|-------------|
| Create quiz | Creates a DRAFT quiz with title, description, and quiz type |
| Add questions | Add any supported question type |
| Per-question timer | `max_time_seconds` configurable per question — available for **all quiz modes** |
| Per-question scoring | `points` and `negative_points` configurable per MCQ question |
| Image support | Upload images for question body and individual MCQ options |
| Question reordering | Drag-and-drop reorder via PUT `/quizzes/{id}/questions/reorder` — DRAFT only |
| Import via Excel | Upload `.xlsx` template to bulk-import questions |
| Export draft to Excel | Download current draft as Excel for offline editing |
| Publish | Transition DRAFT → READY |
| Unpublish | Revert READY → DRAFT |
| Duplicate quiz | Clone a quiz as a new DRAFT |
| Template library | Mark quizzes as templates; create new quizzes from templates |
| Folder organisation | Organise quizzes into named folders |

---

## Live Session (Quiz / Poll)

| Feature | Description |
|---------|-------------|
| Start session | Creates a live session with a unique join code |
| QR code | Auto-generated QR for participant joining; expandable to full-screen |
| Advance / back | Host moves forward or backward through questions |
| Per-question timer | Countdown displayed to host and participants |
| Participant count | Live count of joined participants |
| Leaderboard | Real-time ranking between questions (quiz mode only; polls return 0 scores) |
| Toggle leaderboard | Host can show/hide leaderboard slide |
| End session | Closes session; results frozen |
| Word cloud results | Live word cloud rendered from text answers |
| Profanity filter | Text answers filtered via `better-profanity` |
| Anonymous join | Participants may join without a display name; unique fallback name assigned automatically |

---

## Presenter View

- Dedicated `/present/:sessionId` route optimised for projection screens
- Displays current question, answer distribution, live word cloud, and QR code
- QR code expands to full-screen on click
- Accessible without authentication (public route)

---

## Audience (Participant) Experience

| Feature | Description |
|---------|-------------|
| Join by code | Enter join code at `/join` |
| Join by URL | Direct link `/join/:code` |
| Join by QR | Scan QR code |
| Display name | Optional; unique fallback assigned if blank |
| Answer submission | MCQ select, text input, scale slider |
| Answer feedback | Correct/incorrect shown after question closes (quiz mode) |
| Results view | Answer distribution shown after each question |
| Leaderboard | Personal rank shown (quiz mode) |
| Post-session feedback | Star rating + comment submitted after session ends |

---

## Exam Mode

| Feature | Description |
|---------|-------------|
| Self-paced | Participants start and submit on their own schedule within the configured date window |
| Global time limit | Optional countdown from when the participant clicks "Start Exam"; auto-submits on expiry |
| Per-question time limit | Configurable per question; auto-advances on expiry |
| Individual result | Each participant sees their own score and per-question breakdown on submission |
| Host results dashboard | `/quiz/:id/exam-results` — leaderboard, per-participant score, per-question analytics, integrity report |
| Publish / unpublish | `POST /quizzes/{id}/publish-exam` generates a unique slug and permanent session; `unpublish-exam` reverts to DRAFT |
| Grace period | 10-minute resumption window; attempt locked after expiry or submission |
| Live edit banner | When exam is active (`status=ready`), the builder shows a warning banner; questions are locked from editing |

---

## Proctoring

Optional, per-quiz anti-cheating layer available for **Exam** and **Offline Poll** types. Enabled by the host in the exam builder; availability of rules depends on the tenant's tier.

### Activation

| Step | Details |
|------|---------|
| Host opt-in | Toggle "Enable Proctoring" in the exam builder; off by default |
| Unified save | Proctoring settings and exam metadata (dates, time limit) are saved in a single action |
| Preset levels | **Light Monitoring** (fullscreen + tab-switch), **Standard Security** (+ copy-paste block, multi-tab, bot detection), **Maximum Security** (all available rules for this tier) |

### Browser-Side Rules (FREE tier and above)

| Rule | Trigger | Severity |
|------|---------|---------|
| `fullscreen_enforce` | Participant exits fullscreen | warn |
| `tab_switch_detect` | Tab loses focus or visibility | warn |
| `right_click_block` | Right-click inside exam | warn |
| `copy_paste_block` | Ctrl+C / Ctrl+V / Ctrl+X inside exam | warn |
| `multi_tab_detect` | BroadcastChannel detects another tab | lock |
| `bot_signal_detect` | Missing browser APIs, improbable timing | lock |
| `honeypot_traps` | Hidden fake API URLs / DOM fields triggered | lock (silent) |

### Advanced Rules (PRO+ tiers)

| Rule | Trigger | Severity |
|------|---------|---------|
| `devtools_detect` | DevTools open detected | warn |
| `answer_timing` | Answer submitted faster than minimum plausible time | warn |
| `webcam_monitoring` | Webcam bundle: face absence, multiple faces, gaze away, permission revoked | warn/lock |

### Escalation

Configurable per-quiz:
- **Lock after N violations** — participant receives N−1 warnings then is permanently locked on the Nth
- **Auto-submit on lock** — when enabled, the participant's answers at lock time are automatically submitted; when disabled, a locked participant's answers are not submitted unless they submitted before being locked

### Integrity Report

Available at `/quiz/:id/exam-results` → Integrity tab:

| Column | Description |
|--------|-------------|
| Participant | Display name |
| Score | Total score |
| Integrity Score | 0–100; starts at 100, deducted per violation |
| Violations | Count of violation events |
| Locked | Whether the session was locked |
| Webcam Granted | Whether the participant granted camera permission (PRO+ only) |
| Events | Expandable timeline of all violation events |

Admins can manually lock or unlock any session from the report.

### Key API Endpoints

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| POST | `/proctoring/session/init` | X-Session-Token | Register proctoring session for a participant |
| POST | `/proctoring/session/webcam-granted` | X-Session-Token | Mark webcam permission as granted after browser allow |
| POST | `/proctoring/event` | X-Session-Token | Log a violation event |
| POST | `/proctoring/honeypot` | none | Silent honeypot trap — always returns HTTP 200 |
| POST | `/proctoring/answer-timing` | X-Session-Token | Server-side answer speed validation |
| GET | `/proctoring/config/{quiz_id}` | none | Active rule set for a quiz |
| GET | `/proctoring/report/{quiz_id}` | JWT | Per-participant integrity report |
| GET | `/proctoring/rules` | JWT | Platform rule registry |
| POST | `/proctoring/lock/{token}` | JWT | Admin: manually lock a session |
| POST | `/proctoring/unlock/{token}` | JWT | Admin: manually unlock a session |

---

## Offline Poll Mode

| Feature | Description |
|---------|-------------|
| Public URL | Accessible via `/poll/:slug` without a live host |
| Anonymous participation | No login required |
| Results view | Host views aggregated results at any time |

---

## Session History & Export

Session results accessible from `/quiz/:id/history`. Exportable in four formats:

| Format | Extension |
|--------|-----------|
| Excel | `.xlsx` |
| PDF | `.pdf` |
| Word | `.docx` |
| PowerPoint | `.pptx` |

---

## Tier System

Limits enforced at session start and quiz publish time via `TierService` (Redis-cached, 5-min TTL per tier).

| Tier | Participants / session | Questions / quiz | Concurrent sessions |
|------|----------------------|-----------------|-------------------|
| **Free** | 100 | 10 | 1 |
| **Basic** | 250 | 30 | 2 |
| **Pro** | 2,500 | 100 | 5 |
| **Enterprise** | 10,000 | 1,000 | 50 |

**UI features:**
- Colour-coded tier badge in host header (grey=Free, blue=Basic, purple=Pro, gold=Enterprise)
- Hover on badge shows live limits tooltip (translated in all 11 languages)
- Upgrade banner on Dashboard — always shown for Free; shown for higher tiers when question usage ≥ 70%
- Banner dismissible for 3 days via localStorage
- Super admins can change a user's tier from `/admin/users` → Edit User

---

## Admin Panel

| Page | Access | Features |
|------|--------|---------|
| `/admin/statistics` | admin, super_admin | Platform usage stats and historical snapshots |
| `/admin/users` | admin, super_admin | List users with colour-coded tier badge; edit role, tier, active status; create/delete |
| `/admin/organizations` | super_admin | Manage tenant organisations |
| `/admin/platform-quizzes` | super_admin | View all quizzes across all tenants |
| `/admin/tier-management` | super_admin | Edit tier limits (max_participants, max_questions, max_concurrent_events) |
| `/admin/feedback` | admin, super_admin | View all participant and user feedback submissions |

---

## Internationalisation

11 supported languages; user selection persisted per authenticated session:

| Code | Language |
|------|----------|
| `en` | English (default) |
| `hi` | Hindi |
| `ta` | Tamil |
| `te` | Telugu |
| `ka` | Kannada |
| `bn` | Bengali |
| `gu` | Gujarati |
| `es` | Spanish |
| `fr` | French |
| `de` | German |
| `ru` | Russian |

---

## Authentication

| Feature | Description |
|---------|-------------|
| Register | Email + password (min 8 chars, 1 uppercase, 1 digit) |
| Email verification | Token-based; login blocked until verified |
| Login | JWT issued on success (24h expiry) |
| Forgot / reset password | Token emailed; 1h expiry |
| `/auth/me` | Called on every app load to refresh user/tier data from DB |
| `/auth/my-limits` | Returns current user's tier limits |
| `/auth/tier-plans` | Returns all tiers' limits (used by upgrade banner) |

---

## Regression Test Suite

Automated suites in `scripts/regression/`:

| Suite | Script | Description |
|-------|--------|-------------|
| A — Smoke | `run_preprod_gate.sh` | API health, auth flow, basic quiz CRUD, session lifecycle |
| B — Core | `run_preprod_gate.sh` | Full quiz lifecycle, all question types, answer submission, results |
| C — Negative | `run_preprod_gate.sh` | Invalid inputs, auth failures, tier constraint violations |
| D — Extended | `run_preprod_gate.sh` | Text question types, live poll mode, question reorder, anonymous participant, question field persistence |
| E — UI | `run_preprod_gate.sh` | Selenium browser tests via `selenium-arm` Docker container |
| Exam Lifecycle | `test_exam_lifecycle.py` | Create→publish→start→answer→submit→result→unpublish; includes UTC timezone assertion on `started_at` |
| Proctoring | `test_proctoring.py` | 10-phase regression: rule registry, session init/idempotency, escalation/locking, admin lock/unlock, tier filtering, violation report, answer timing, watermark, integrity scorer, webcam-granted endpoint, unified save |
