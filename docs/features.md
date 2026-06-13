# Features

## Activity Types

Swaya supports four distinct activity types, each designed for a different engagement scenario.

---

### Live Quiz

A real-time, host-driven competitive quiz.

**Flow:**
1. Host creates a quiz with MCQ questions (manually, from a template, from Excel import, or via AI generation).
2. Host publishes the session → gets a 6-character join code and QR code.
3. Audience joins at `swaya.me/join` by entering the code — no login, no app install.
4. Host controls pace: advances questions manually.
5. After each question, a live leaderboard is shown.
6. Final leaderboard displayed at end; host can export results to PDF, Excel, or PowerPoint.

**Audience capacity:** enforced by tier (FREE: 50, higher tiers: up to 500+).

**Question types in live quiz mode:** MCQ with configurable time limit per question.

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

### Offline Poll

A self-service poll that runs without an active host.

**Flow:**
1. Host creates an offline poll and publishes it.
2. A QR code is generated that links directly to the poll URL.
3. Audience scans the QR and answers at their own pace — no host presence needed.
4. Host views aggregated results at any time.

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
7. Host views full results dashboard: leaderboard, per-question analytics, per-participant breakdown.
8. Host can trigger result emails to all participants (or schedule the nightly batch).

**Proctoring (optional):**
- Webcam snapshots captured client-side via MediaPipe face detection (WASM, no external service).
- Snapshots stored server-side; host can review per-participant.
- Tab-switch and focus-loss events recorded; repeat violations can block submission.

**AI analysis:** Host can request a Gemini-generated summary of class performance after at least one submission.

---

## AI Features

### Question Generation

- Input: a topic or custom prompt + target language + question count.
- Gemini 2.0 Flash generates MCQ questions with distractors.
- Optional: Ollama (local) for offline distractor generation and question rewriting.
- Generated questions are editable before saving.

### Result Analysis

- After exam completion, host can trigger AI analysis via the results dashboard.
- Gemini receives anonymized per-question statistics (pass rate, most-common wrong answer, etc.).
- Returns a structured summary suitable for inclusion in a report.

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

The UI is available in 11 languages switchable at runtime:

English · Hindi · Tamil · Telugu · Kannada · Bengali · Gujarati · Spanish · French · German · Russian

Database-stored content (question text, options) is authored by the host and is never machine-translated by the platform.

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
