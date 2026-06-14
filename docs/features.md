# Features

## Activity Types

Swaya.me supports four distinct activity types, each designed for a different engagement scenario.

---

### Live Quiz

A real-time, host-driven competitive quiz.

**Flow:**
1. Host creates a quiz with MCQ questions (manually, from a template, from Excel import, or via AI generation).
2. Host publishes the session → gets a 6-character join code and QR code.
3. Audience joins at `swaya.me/join` by entering the code — no login, no app install.
4. Host controls pace from the live cockpit: advances questions manually.
5. After each question, a live leaderboard is shown.
6. Final leaderboard displayed at end; host can export results to PDF, Excel, or PowerPoint.

**Audience capacity:** enforced by tier (FREE: 50, higher tiers: up to 500+).

**Question types in live quiz mode:** MCQ with configurable time limit per question. Questions can include embedded YouTube/Vimeo video.

---

### Live Poll

A host-driven poll for gathering real-time audience opinions.

**Flow:**
1. Host creates a poll with one or more questions.
2. Audience joins via the same join-code flow as a live quiz.
3. Results displayed live as audience submits answers.

**Supported question types:**
- **MCQ** — single-choice from options
- **Word Cloud** — free-text responses rendered as a live word cloud (automatic profanity filtering)
- **Scale** — 1–10 rating slider
- **Single Line** — short free-text
- **Paragraph** — long free-text
- **One Word** — constrained single-word response

---

### Offline Poll (Survey)

A self-service poll that runs without an active host.

**Flow:**
1. Host creates an offline poll and publishes it.
2. A QR code is generated that links directly to the poll URL.
3. Audience scans the QR and answers at their own pace — no host presence needed.
4. Host views aggregated results at any time from the Results Hub.

Ideal for physical spaces: conference posters, restaurant tables, trade show booths.

---

### Exam Mode

A self-paced, proctored exam with OTP email verification.

**Flow:**
1. Host creates an exam with questions and configures: duration, open/close dates, proctoring on/off.
2. Host publishes the exam — generates a unique slug URL (e.g., `swaya.me/e/xyz123`).
3. Participant navigates to the exam URL, enters name + email.
4. A 6-digit OTP is emailed to them. They enter it to start.
5. All questions are delivered at once; participant answers and submits before the timer expires.
6. Immediate results displayed to participant (score, correct/incorrect breakdown).
7. Host views full results dashboard: leaderboard, per-question analytics, per-participant breakdown, and per-candidate integrity reports.
8. Host can trigger result emails to all participants (or schedule the nightly batch).

**Proctoring (optional):**
- Webcam snapshots captured client-side via MediaPipe face detection (WASM, no external service).
- Snapshots stored server-side; host reviews them on a per-candidate integrity report with a visual timeline.
- Tab-switch, fullscreen exit, copy-paste, and focus-loss events recorded as violation events.
- Violations contribute to an integrity score (0–100) per candidate.
- Final score is automatically adjusted based on the integrity score.
- Host can lock a candidate out mid-exam.
- Violation timeline and snapshot grid are downloadable as evidence.

**AI analysis:** Host can request a Gemini-generated summary of class performance after at least one submission.

---

## Home Dashboard

The home page works as a live briefing for the host:

- **Up Next** — ready activities surfaced front and centre with one-click Run, join-link copy, and QR display.
- **Continue Editing** — recent drafts always visible; drafts with zero questions are flagged with a warning.
- **Last Session** — participant count, average score, and accuracy from the most recent session, with one-click access to the full recap.
- **Folders in the sidebar** — activities can be organised into nested folders; folders are draggable and shareable with teammates.

---

## Activities Page

A dedicated full-library view for all activities a host has created:

- Filter by activity type (Quiz, Poll, Exam, Survey) and status (Ready, Draft, Archived).
- **Needs Attention** filter surfaces drafts with zero questions instantly.
- **Archive instead of delete** — archived activities retain all historical results; toggle to show/hide them.
- **Bulk actions** — select multiple activities and archive or delete in one operation.

---

## Results Hub

A unified view of all session results across all activity types:

- All live quiz, poll, exam, and survey sessions in one searchable, filterable list.
- Filter by mode (quiz/poll/exam/survey), status, or title.
- One-click navigation to the full recap for any session.
- Replaces the previous per-quiz results pages scattered across the app.

---

## Template Gallery

A browsable library of ready-made activities:

- Templates available for quizzes, polls, and surveys.
- Click **Use this template** to create a fully populated activity ready to publish and run.
- Eliminates the blank-page problem for new hosts.

---

## Live Host Cockpit

The host session control interface, redesigned as a two-pane layout:

- **Left pane (stage)** — mirrors exactly what the audience/projector sees.
- **Right pane (controls)** — question navigation, timer, participant count, leaderboard toggle. Always visible; no scrolling mid-session.
- Join code and QR pinned at all times, even after page refresh, so latecomers can always join.
- **Participant lobby** — names appear as participants join before the session starts.
- **Session recap page** — after stopping, host lands on a recap (podium, per-question accuracy, hardest question, export) instead of a blank page.

---

## Participant Skins

Hosts can set a visual skin per quiz that changes the look and feel of the audience-facing participant screens:

| Skin | Feel |
|---|---|
| Default | Clean, neutral |
| Classroom | Warm, chalk-and-board feel |
| Boardroom | Professional, muted greens |
| Party | Vibrant, festive purples |

Skins apply automatically to all participant devices — participants do nothing.

---

## Video in Questions

Any question (quiz, poll, or exam) can include an embedded video:

- Paste a YouTube or Vimeo URL into the question editor.
- The video renders as an embedded player visible to participants before they answer.
- Useful for listening comprehension, case studies, training scenarios, and visual identification questions.

---

## AI Features

### Question Generation

- Input: a plain-language prompt (e.g. *"10 questions on the French Revolution for Grade 10, challenging"*) + target language + question count.
- Gemini 2.0 Flash generates a fully formed activity — title, description, all questions pre-filled — streamed live as a preview.
- **Voice input** — hosts can speak the prompt instead of typing.
- **Image suggestions** — for visual topics, AI suggests image search queries per answer option to help hosts find and attach relevant images quickly.
- Generated questions are individually editable inline before adding to the quiz.
- Works across all four activity types: Quiz, Poll, Exam, Survey.
- Optional: Ollama (local) for offline distractor generation and question rewriting.

### Exam Result Analysis

- After exam completion, host can trigger AI analysis via the results dashboard.
- Gemini receives anonymised per-question statistics (pass rate, most-common wrong answer, etc.).
- Returns a structured performance summary suitable for inclusion in a report.

---

## Word Cloud

- Audience submits free-text responses to a word-cloud question.
- Real-time rendering using D3.js word-cloud layout.
- Automatic profanity filtering on the backend before display.
- Configurable max response length.

---

## Export

| Format | Scope |
|---|---|
| PDF | Quiz/exam summary report with charts |
| Excel (.xlsx) | Raw answer data, participant list |
| PowerPoint (.pptx) | Slide deck of results for classroom/presentation use |

---

## Question Import

Hosts can bulk-import questions from a structured Excel file (`.xlsx`). The import service:
- Validates required columns (question text, correct answer index, options).
- Sanitizes all input (HTML and plain text) before saving.
- Reports import errors per-row.

---

## Multi-language Support

The UI is available in 11 languages, switchable at runtime from the header:

English · Hindi · Tamil · Telugu · Kannada · Bengali · Gujarati · Spanish · French · German · Russian

Database-stored content (question text, options) is authored by the host and is never machine-translated by the platform.

---

## UI Themes

Three visual themes are available, switchable from the header without reloading:

| Theme | Character |
|---|---|
| Classic Indigo | Default; clean professional indigo |
| Funky-Studio | Bold, high-contrast, creative |
| Perky-Game | Playful, game-show energy |

---

## Progressive Web App (PWA)

Swaya.me is installable as a PWA on any device:
- Tap **Add to Home Screen** on mobile or use the install prompt on desktop.
- Loads instantly from cache; works offline for the host dashboard.
- No app store required.

---

## Feedback & Analytics

- In-app feedback widget available on all pages.
- Platform event beacons (`/api/v1/metrics/event`) record page views, quiz starts, answer submits, and errors for internal analytics — fire-and-forget, never blocks a user request.

---

## Admin Features (Tenant Admin)

- User management: invite, deactivate, change role.
- Tier and usage overview.
- Feedback management: view all in-app feedback submissions.
- AI analysis endpoint for exam results.
- Participant email delivery: manual trigger or nightly batch.

---

## Accessibility

Participant screens and exam surfaces meet ARIA standards:
- Screen-reader friendly landmarks and labels.
- Fully keyboard-navigable.
