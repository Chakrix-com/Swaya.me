# Swaya.me — Product & UX Reimagining Review

**Reviewer:** Claude (Fable 5) · **Date:** 2026-06-11
**Environment reviewed:** `test.swaya.me` (logged in as `demo@swaya.me`, ENTERPRISE tier)
**Method:** Hands-on Selenium walkthroughs of every major journey — visitor landing, login, dashboard, quiz builder, template library, live quiz session (host control room + participant on a phone-sized window simultaneously), live poll with all question types, exam creation → publish → candidate taking → host results, offline poll, session history, plans, theme picker. ~60 screenshots and text dumps captured in `/tmp/fable-review/`.

---

## 1. Executive summary

Swaya.me is functionally rich — genuinely more capable than its UI lets on. Four activity modes (live quiz, live poll, offline poll, proctored exam), six question types, folders, templates, AI-assisted authoring hooks, integrity-scored exam results with PDF export and "email results to participants", a projector presentation mode with whiteboard, theming, and 11-language i18n. The new test-env landing page ("One room. Every voice.") is excellent — confident, characterful, and it sells the product far better than the production one.

The core problem is that **the product's quality is uneven across the journey**. The landing page promises a premium experience; the dashboard delivers a dense admin table; the host's live control room buries its most important button below the fold; and the participant — the person the product exists for — gets the *least* designed experience of all, including a feedback state that visually tells them their **correct answer was wrong**.

The reimagining below is organized around one principle: **design each surface for the person standing in front of it** — the host on a laptop mid-presentation, the participant on a phone held in one hand, the candidate under exam stress, and the organizer reviewing results afterwards.

---

## 2. What exists today (journey inventory)

### 2.1 Visitor → signup
- Landing page (test env): hero with live join-code input, "three instruments" framing (Quiz = energy, Poll = honesty, Test = when it counts), trust section (auto-scoring, webcam snapshots, exports, 11 languages). Strong copy, good visual rhythm.
- Login: clean centered card, Google OAuth, forgot-password. Fine.
- Join-a-session is reachable from the landing hero — good instinct, participants are the top traffic.

### 2.2 Host: create → run → review
- **Dashboard**: welcome hero + 4 create cards (Online Quiz / Test / Online Poll / Poll) + 3 stat tiles (176 Ready to Launch / 92 In the Works / 0 Past Sessions) + a paginated table of all activities + folder tree in the sidebar.
- **Builder**: title/description (with AI "Rewrite" and lightning-bolt affordances), question list, "Generate with AI", Add Question, per-type settings (dates for exams/offline polls), publish/unpublish lifecycle. Settings lock while published ("Settings are read-only — unpublish to edit").
- **Control room** (`/quiz/:id/control`): Present button (F5), Stop Quiz, title card, participants count, status, QR + join URL + 6-digit code, leaderboard panel with show/hide-from-participants, then the live question with response bars, correct answer, Previous/Next Question — *all stacked vertically on one long page*.
- **Present view** (`/present/:sessionId`): genuinely good-looking dark projector screen — question, options with live bars, participant count, keyboard hints, Stop, Whiteboard toggle.
- **History**: list of sessions (LIVE/ENDED, participants, responses, Export per row, expandable rows).
- **Exam results**: a standout page — Started/Completed/Abandoned/Average tiles, integrity-merged leaderboard (score, %, time, integrity score, adjusted rank, violations, "Clean" status), question analytics, Download PDF Report, "Send Results to Participants" with sender name.

### 2.3 Participant
- `/join`: code + optional name ("anonymous if blank") card.
- Waiting room: spinner + "Waiting for quiz to start…".
- Question view: A/B/C/D boxes, Submit Answer, then live result bars + "Waiting for next question…" + leaderboard with "Your Rank: #1".
- Poll question types render correctly on mobile width: MCQ, single-line, scale (tap-a-star), paragraph; word cloud supported.
- Exam taking (`/e/:slug`): excellent entry page — question count, closes-at, scoring rules chips ("+1 for correct", "No penalty for wrong"), timer warning, name field; per-question countdown with progress bar; auto-advance; "Your Score 2 / 2" trophy screen with "Create your own polls & quizzes" CTA.

### 2.4 Admin (super_admin)
Statistics, User Management, Organizations, Platform Quizzes, Tier Management, Feedback — tucked into the avatar dropdown. Platform stats sidebar widget on prod dashboard.

---

## 3. Bugs and friction found during the walkthrough (evidence-backed)

These are concrete, reproducible findings from this session:

1. **Control room loses join info on reattach.** If a session is already running (started elsewhere, or the host refreshes/returns), the control room renders `Join URL: https://test.swaya.me/join/undefined` and `Join Code: 0`, with a QR encoding the bad URL. Reproduced twice (sessions 1842, 1844). A host who closes their tab mid-event cannot get the code back without restarting. **This is the single most dangerous live-event failure in the product.**
2. **Participant's correct answer is styled as wrong.** After submitting "Paris" (correct), the participant's selected option shows a **red border + red ✗ icon** (screenshot `a03`). Score increments correctly (leaderboard says #1), so it's pure presentation — but a classroom of students seeing red ✗ on right answers is a trust-killer.
3. **Session end doesn't reach participants promptly.** After host Stop, the participant stayed on "Waiting for next question…" (screenshots `a09`). Cause: all realtime state is HTTP polling (`setInterval` 2–3s in `AudienceSession.jsx` / `QuizControl.jsx`) and the ended state appears not to be handled distinctly from "waiting".
4. **Deleting a quiz with exam sessions 500s.** `DELETE /quizzes/1001` → `IntegrityError: Column 'quiz_id' cannot be null` on `quiz_sessions`. Cleanup of test/finished activities is impossible once an exam has been taken. (My temp draft "Fable Review Temp Exam", id 1001, is still on test for this reason — delete it once fixed.)
5. **Host's primary action is below the fold.** In the control room, "Start First Question" / "Next Question" sit at the bottom of a long page, under the QR block and leaderboard. During pass 3 my automation — like a real host — couldn't find the button without scrolling. The one thing a host does 30 times per session should never require scrolling.
6. **The four create labels are a riddle.** "Create Online Quiz" vs "Create Test" vs "Create Online Poll" vs "Create Poll" — "Poll" secretly means *offline* poll, "Test" means exam. The landing page already solved this with intent language ("when you want energy / honesty / when it counts"); the app doesn't use it.
7. **Dashboard is a workload, not a workspace.** 268 activities in a flat paginated table, dozens named "test", "b", "nnnnnnnnn", drafts with 0 questions. Stat tiles say "176 Ready to Launch" — counting regression debris. No recency, no "what should I do next", no pinning, no archive.
8. **Stop Quiz confirmation is easy to miss** (popconfirm anchored top-right while the host's attention is at the bottom controls), and "You cannot restart it" is a hard stop with no "are results saved?" reassurance beyond a tooltip.
9. **Prod vs test divergence**: production still serves the old "Interactive Quizzes Made Simple" landing and an admin-style dashboard with platform stats in the sidebar for a demo user. The redesign on test is clearly the right direction — ship it.
10. Minor: `/join` page is branded "Join Quiz" even for polls; exam entry shows closing time as "23:59, 12 Jun" with awkward wrapping; participant page keeps a disabled "Submit Answer" button visible after submitting; "1 Questions" pluralization; template library is a one-row table inside a modal — undersells a key growth feature.

---

## 4. The reimagined product

### 4.1 North star

The landing page already states it: **"One room. Every voice."** The product should feel like *running a room*, not administering records. Every redesign below pushes one of three feelings:
- **Host:** "I am in control and I look good doing this."
- **Participant:** "That was fun / fair / worth my 10 minutes."
- **Organizer afterwards:** "I can prove what happened and act on it."

### 4.2 Information architecture

Rename the four modes everywhere using the landing page's own language, and reorganize navigation around *the loop* (create → run → results) instead of around object types:

| Today | Reimagined | One-liner |
|---|---|---|
| Online Quiz | **Live Quiz** | energy — leaderboard, speed points |
| Online Poll | **Live Poll** | honesty — anonymous, word clouds |
| Poll (offline) | **Survey** | async link, collect anytime |
| Test/Exam | **Test** | when it counts — timed, proctored |

Sidebar: **Home · Activities (folders, templates, archive) · Results · [Join a session] · Settings**. Admin stays behind the avatar. "Results" becomes a first-class destination unifying session history, survey responses, and test results — today these live on three different per-quiz pages that are hard to even find (history is behind a per-row button).

### 4.3 Dashboard → "Home"

Keep the welcome hero and create cards, but make the page *time-based, not table-based*:
- **"Up next"** strip: activities scheduled/ready, with one-click **Run** / **Copy link** / **QR**.
- **"Continue editing"** strip: 3 most recent drafts.
- **"Last session"** card: headline numbers + "view results" deep link.
- The full table moves to **Activities**, gaining: archive (hide the noise without delete), bulk actions, sort by last-run, and a "needs attention" filter (drafts with 0 questions, expired tests still published).
- Stat tiles should count *meaningful* things: "3 sessions this week, 142 participants, 87% avg score" — not raw row counts.

### 4.4 Host live experience — the control room becomes a cockpit

This is the highest-impact redesign. Replace the long scrolling page with a **two-pane cockpit** that never scrolls during a session:

```
┌────────────────────────────────────────────┬──────────────────┐
│  STAGE (what the room sees, mirrored)      │  CONTROL RAIL    │
│                                            │  ● LIVE 00:12:33 │
│  Q3/6 · What is the capital of France?     │  👥 47 joined    │
│  [A London ▓▓░ 12%] [B Paris ▓▓▓▓ 61%] …   │  ✔ 39 answered   │
│                                            │  ────────────    │
│                                            │  [▶ Next]  big   │
│                                            │  [↺ Back][⏸ ]    │
│                                            │  [🏆 Leaderboard]│
│  join bar (pinned): code 567353 · QR ⤢     │  [⬛ Present F5]  │
└────────────────────────────────────────────┴──────────────────┘
```

- **Join code pinned and huge at all times** (also fixes finding #1 by design — and the code must rehydrate from the server on every load).
- **Next** is a fixed, keyboard-driven (Space) primary button; response progress ("39/47 answered") sits right next to it so the host knows *when* to advance — the single most common host decision, currently unsupported.
- Stage pane mirrors the Present view so the host sees exactly what the projector shows; Present (F5) just fullscreens it.
- End-of-session takes the host straight to a **session recap** (podium, per-question accuracy, hardest question, export) instead of dumping them back on a static page. Today after Stop, results hide in History.
- Pre-session **lobby** becomes a moment: names popping in as they join, a "warm-up" toggle (emoji wall / word cloud) so early joiners aren't staring at a spinner.

### 4.5 Participant experience — from form to game

The participant UI is functional but emotionally flat, and it's the surface seen by 100× more people than any other. Reimagined journey:

1. **Join** (`/join` or QR): after entering the code, show *what they're joining* — activity title, host name, mode chip — before they commit a name. Offer fun anonymous identities ("Brave Falcon") instead of a blank field.
2. **Lobby**: show "You're in — 46 others here", host's title slide, an emoji-react wall. Phone stays awake (wake lock).
3. **Question**: full-screen one-thing-at-a-time card, large tap targets (already decent), a visible timer ring synced with the host, optimistic submit (instant lock-in + "Locked in! ⚡ 3rd fastest").
4. **Reveal**: green/red done *correctly* (fix #2), +points animation, position delta ("▲ 2 places"). For polls: animated bars/word cloud forming live.
5. **Leaderboard moments**: top-3 podium full screen, "you" row always pinned even at rank #38.
6. **Session end**: a real finale — confetti for top 3, personal summary ("4/6 correct, fastest on Q2"), then the existing conversion CTA ("Create your own — free"). Today they get a hung "Waiting for next question…" (#3) — the worst possible last impression, and the moment with the highest viral potential.
7. **PWA**: installable, reconnect-safe (rejoin with same token after a network blip — phones lock constantly in rooms).

### 4.6 Test/exam experience

Already the most mature journey (entry page with scoring rules is genuinely excellent; integrity-merged results table is a competitive differentiator). Polish, don't rebuild:
- Candidate: question palette/progress ("3 of 20, 2 flagged"), explicit "no going back" warning *per design or removal of it*, autosave indicator, low-time visual urgency, a post-submit "what happens next" (when results email arrives).
- Host: bring exam scheduling (open/close windows, seat limits) into a clear "Distribute" step — today dates hide in builder settings; surface the superb results page in the unified Results area; add per-question item analysis (difficulty/discrimination) — data already exists.
- Proctoring (webcam snapshots, violations, adjusted rank) deserves a dedicated, sober "Integrity report" view per candidate — it's currently columns squeezed into a wide table requiring horizontal scroll.

### 4.7 Creation & authoring

- **Intent-first create**: one "Create" button opening the landing page's triad — "I want energy / honesty / it counts" → mode preselected. Keep direct cards for power users.
- **AI as the default fast path**: "Generate with AI" exists but is buried mid-builder. Make "Describe your session → get a draft" the hero of the create flow (topic, audience, count, difficulty, language — leveraging the 11-locale support).
- **Template gallery**: replace the one-row modal table with a browsable gallery (cards, preview, category, "used 287 times") and seed 20–30 quality templates per vertical (classroom, all-hands, training, hiring).
- Builder ergonomics: inline question editing in a single column with live phone-frame preview on the right (the participant view *is* the artifact being designed); drag-reorder; duplicate question; bank/reuse questions across activities; Excel import already exists — surface it.
- Publish/unpublish lifecycle is sound but the read-only lock needs a one-click "Unpublish & edit" with auto-republish prompt, not a yellow warning banner and hunt for buttons.

### 4.8 Look & feel

A coherent design language, derived from the new landing page (which is already the best-designed artifact in the product):

- **Tokens**: continue the `--sw-*` CSS variable work; define a single scale for color/type/space/radius/shadow used by landing, app, and participant surfaces. Today: landing (serif-accented editorial) ≠ app (stock Ant ProLayout) ≠ participant (plain light cards) ≠ present view (dark violet). Four dialects, one brand.
- **Mode accents**: the landing already color-codes Quiz/Poll/Test chips — carry one accent hue per mode through builder, control room, participant, and results so the room instantly "knows what game we're playing".
- **Type**: pair the landing's display serif (headlines, scoreboard moments, "Your Score") with the existing sans for UI. The participant reveal and podium screens are where typographic drama pays off.
- **Motion**: a small motion system (bar fills, rank shuffles, count-ups, confetti) — live audience products *are* motion; today nothing moves except spinners.
- **Themes**: current picker (Classic Indigo / Funky-Studio / Perky-Game) restyles the host chrome only. Reframe theming as **host-chosen session skins that the *participants and projector* see** (Classroom, Boardroom — mockups already in repo —, Party). The host's own admin chrome needs exactly two: light/dark.
- **Density & furniture**: kill the GitHub icon and BETA badge inside the logged-in app header; tier badge belongs in account menu; footer legal links shouldn't render inside the live control room; fix "1 Questions", "0 (0.0%)" noise on participant reveals.

### 4.9 Architecture enablers (what the UX needs from the backend)

- **WebSocket or SSE for session state** (Redis pub/sub is already in the stack), replacing 2–3s polling: sub-second advance/reveal propagation, "N answered" live on host, instant end-of-session screens, and lower load than polling 10k participants (tier max). Keep polling as a degraded fallback.
- **Session state machine hardening**: `created/started/active/ended` semantics surfaced consistently (fixes the undefined-join-code rehydration and the ended-state limbo); idempotent reattach for both host and participant.
- Fix the delete cascade for quizzes with exam sessions (#4); add archive as the soft path.
- Server-authoritative timers (countdown drift between host/participant is visible today).

---

## 5. Prioritized roadmap

**P0 — Trust (this sprint): fix what breaks live rooms.**
1. Control-room join code/URL rehydration on reload/reattach (#1)
2. Correct-answer shown red on participant reveal (#2)
3. Session-ended state for participants + recap screen stub (#3)
4. Quiz delete FK 500 (#4) + archive action

**P1 — The live loop (next 2–4 weeks): cockpit + participant reveal.**
Control-room two-pane layout with pinned code and answered-counter; participant reveal/leaderboard/finale animations; "N answered" for hosts; WebSocket/SSE channel behind a flag.

**P2 — The shop window: home, create, templates.**
Home redesign (Up next / Continue / Last session), Activities with archive+filters, intent-first create with AI generation as the hero, template gallery, mode renames (Live Quiz/Live Poll/Survey/Test) across UI + i18n (the 71-key home.v2 translation work shows the pipeline exists).

**P3 — Coherence: design system + results hub.**
Token unification across landing/app/participant/present, mode accent system, unified Results area, exam integrity report view, session skins v1.

**P4 — Reach: PWA participant, reconnect resilience, public quiz discovery, self-serve plan upgrades (the Plans page currently ends in "email us"), team workspaces on the existing tenant/role model.**

**Success metrics:** participant rejoin rate after disconnect; % sessions where host never scrolls/never loses code (instrument it); participant finale→signup conversion; time-to-first-published-activity for new hosts; weekly active hosts running ≥1 session.

---

## 6. Appendix

### Artifacts
- Screenshots/text dumps: `/tmp/fable-review/` (passes 1–5: `01–06` public+dashboard, `10–42` builder/live/poll/themes, `a01–a10` live quiz with answers, `b01–b04` exam builder, `c01–c09` exam taking + results).
- Exploration scripts (reusable as journey smoke tests): `scripts/fable_explore_1.py` … `fable_explore_5.py`.

### Test-data notes (test env)
- Live sessions 1842–1845 for quiz 11 and 1844 for poll 46 were created and **all ended**; a few extra "1 participant / 0–2 responses" rows now appear in Demo Quiz history.
- Draft **"Fable Review Temp Exam" (quiz id 1001)** could not be deleted due to bug #4 — remove it after the FK fix (its 1-response twin from pass 4, id 1000, deleted fine before taking responses; id 999 deleted fine).
- One exam response by "Fable Reviewer / fable@example.com" exists on quiz 1001.

### What I'd verify next (not covered this pass)
Webcam-snapshot proctoring UX during a live exam, whiteboard collaboration in Present view, word-cloud rendering with many participants, folder drag-and-drop, Excel import/export round-trip, admin Statistics/Tier Management screens, and the non-English locale experience end-to-end.
