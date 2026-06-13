# Fable Review — Implementation Plan & Tracker

**Source:** [`fable_review.md`](../fable_review.md) (UX/product review, 2026-06-11)
**Owner:** —  **Created:** 2026-06-11  **Last updated:** 2026-06-12

This plan converts every suggestion in the Fable review into trackable work items.
Update the Status column / checkboxes as work progresses. Keep this file as the single source of truth for the initiative.

**Status legend:** `⬜ todo` · `🟦 in progress` · `🟨 in review/on test` · `✅ done (live)` · `⛔ blocked` · `🚫 won't do`

**Definition of Done (every item):** code merged → all new user-visible strings have keys in **all 11** `frontend/src/locales/*/translation.json` files → frontend built → deployed to test env (`sudo systemctl restart swayame-backend-test.service` if backend) → Selenium-verified on test.swaya.me (scripts in `scripts/fable_explore_*.py` are reusable smoke tests) → human approval → `./deploy.sh promote-live`.

---

## Dashboard

| Phase | Theme | Items | Done |
|---|---|---|---|
| **P0** | Trust — live-room bugs | 5 | 5/5 ✅ |
| **P1** | The live loop — host cockpit + participant game | 12 | 12/12 ✅ |
| **P2** | The shop window — home, create, templates | 8 | 8/8 ✅ |
| **P3** | Coherence — design system + results hub | 9 | 1/9 |
| **P4** | Reach — PWA, self-serve, workspaces | 7 | 0/7 |
| **X** | Cross-cutting — instrumentation, QA, cleanup | 6 | 0/6 |
| | **Total** | **47** | **26/47** |

---

## Journey blueprints — what each actor sees, screen by screen

> Target-state designs the work items build toward. Each blueprint lists the journey as a state flow, then a wireframe per screen. Items reference these as **[J1]**…**[J6]**. Wireframes are layout intent, not pixel specs; all participant screens are phone-first (≤430 px), host screens are laptop-first (≥1366 px).

### J1 — Host: idea → published activity
**Flow:** `Home → Create (intent chooser) → AI draft or blank → Builder (edit + live phone preview) → Publish → Up next on Home`
**Items:** P2-2, P2-3, P2-4, P2-8, P2-1.

**J1a · Home (logged-in host)** — time-based, not table-based:
```
┌──────────────────────────────────────────────────────────────┐
│ ☰ Swaya   Home · Activities · Results          🔍  ⚙  (D)   │
├──────────────────────────────────────────────────────────────┤
│  Welcome back, Demo 👋                    [ + Create ]       │
│                                                              │
│  UP NEXT                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ LIVE QUIZ    │ │ TEST         │ │ LIVE POLL    │          │
│  │ Class 7 Maths│ │ Python Screen│ │ Town Hall    │          │
│  │ 5 questions  │ │ open till Fri│ │ 4 questions  │          │
│  │ [▶ Run] [QR] │ │ [🔗 Copy link]│ │ [▶ Run]      │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│                                                              │
│  CONTINUE EDITING                LAST SESSION                │
│  · ISC Java draft (30 q)  ✏️      Demo Quiz — yesterday      │
│  · Feedback survey (3 q)  ✏️      47 joined · 78% correct    │
│  · Onboarding quiz (0 q)  ⚠️      [View recap →]             │
│                                                              │
│  This week: 3 sessions · 142 participants · 87% avg score    │
└──────────────────────────────────────────────────────────────┘
```

**J1b · Create — intent chooser** (landing-page language carried into the app):
```
┌──────────────────────────────────────────────────────────────┐
│            What does this moment need?                       │
│                                                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌────────────────┐  │
│  │ ⚡ ENERGY        │ │ 🤝 HONESTY      │ │ 🎯 IT COUNTS   │  │
│  │ Live Quiz       │ │ Live Poll       │ │ Test           │  │
│  │ leaderboard,    │ │ anonymous, word │ │ timed, graded, │  │
│  │ speed points    │ │ clouds, pulse   │ │ proctored      │  │
│  └─────────────────┘ └────────┬────────┘ └────────────────┘  │
│                               └ async? → Survey (link)       │
│                                                              │
│  ✨ Or describe it and let AI draft it:                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ "10 questions on photosynthesis for class 9, Hindi"    │  │
│  └────────────────────────────────────────────[Generate]──┘  │
└──────────────────────────────────────────────────────────────┘
```

**J1c · Builder — edit left, participant truth right:**
```
┌───────────────────────────────────────────┬──────────────────┐
│ ← Activities   Class 7 Maths   ● Draft    │   PHONE PREVIEW  │
│ [✨ Generate] [⬆ Import] [▶ Preview run]  │  ┌────────────┐  │
│                                           │  │ Q2 · 0:30  │  │
│ ⠿ Q1  MCQ   What is 12 × 8?          ✏️ ⧉ 🗑│  │ What is    │  │
│ ⠿ Q2  MCQ   What is 144 ÷ 12?  ◀ editing  │  │ 144 ÷ 12?  │  │
│   ┌─────────────────────────────────────┐ │  │ ┌────────┐ │  │
│   │ Question: What is 144 ÷ 12?         │ │  │ │   10   │ │  │
│   │ ○ 10   ● 12 ✓   ○ 14   ○ 24   [+opt]│ │  │ │   12   │ │  │
│   │ ⏱ 30s · 1 pt · explanation…         │ │  │ │   14   │ │  │
│   └─────────────────────────────────────┘ │  │ │   24   │ │  │
│ ⠿ Q3  Scale  Rate today's class      ✏️ ⧉ 🗑│  │ └────────┘ │  │
│ [+ Add question]                          │  └────────────┘  │
│                            [Publish ▸]    │  (updates live)  │
└───────────────────────────────────────────┴──────────────────┘
```

---

### J2 — Host: running a live session (the cockpit)
**Flow:** `Up next [Run] → Lobby cockpit → Q1…Qn (advance on "N answered") → Leaderboard moments → Stop (confirm) → Recap`
**Items:** P0-1, P1-1…P1-7, P1-9, P1-11 (projector view), P3-9 (poll visualizations).
**Invariants:** join code always visible · primary action always top-right rail · zero scrolling · Space = next, F5 = present.

**J2a · Lobby (waiting for the room):**
```
┌────────────────────────────────────────────┬──────────────────┐
│  STAGE                                     │ CONTROL RAIL     │
│                                            │ ○ READY          │
│        Class 7 Maths                       │ 👥 12 joined     │
│        Hosted by Demo                      │ ──────────────   │
│                                            │ ┌──────────────┐ │
│   JOIN AT swaya.me/join   ┌─────────┐      │ │ ▶ START FIRST│ │
│   CODE  567 353           │ QR code │      │ │   QUESTION   │ │
│                           └─────────┘      │ └──────────────┘ │
│                                            │ [⬛ Present  F5] │
│   Ria joined · Arjun joined · +10 more ✦   │ [🎉 Warm-up]     │
│                                            │ [✕ Cancel]       │
└────────────────────────────────────────────┴──────────────────┘
```

**J2b · Live question — the screen the host lives on:**
```
┌────────────────────────────────────────────┬──────────────────┐
│  STAGE (mirrors projector)      code 567353│ ● LIVE  00:12:33 │
│                                            │ 👥 47 joined     │
│  Q3/6                            ⏱ 0:18    │ ✔ 39 answered ▂▅█│
│  What is the capital of France?            │ ──────────────   │
│                                            │ ┌──────────────┐ │
│  [A London   ▓▓░░░░░░░░ 12%]               │ │ ▶ NEXT  ⎵    │ │
│  [B Paris    ▓▓▓▓▓▓▓░░░ 61%]               │ └──────────────┘ │
│  [C Berlin   ▓▓░░░░░░░░ 15%]               │ [↩ Back][⏸ Pause]│
│  [D Madrid   ▓░░░░░░░░░ 12%]               │ [🏆 Leaderboard ]│
│                                            │ [⬛ Present  F5] │
│  ✓ correct: B (revealed on advance)        │ [✏ Whiteboard ]  │
│                                            │ [⏹ Stop quiz ]   │
└────────────────────────────────────────────┴──────────────────┘
```
Host decision support: the **39/47 answered** counter beside NEXT is what tells the host *when* to advance — never guesswork.

**J2c · Stop → confirm → recap:**
```
 [⏹ Stop quiz] ─► │ End session for 47 participants?      │
                  │ Results are saved to History.          │
                  │        [Keep playing] [End session]    │
                  ▼
┌──────────────────────────────────────────────────────────────┐
│  SESSION RECAP — Class 7 Maths · today 14:02 · 47 joined     │
│   🥇 Ria 5/6   🥈 Arjun 5/6   🥉 Meera 4/6                    │
│  Accuracy by question:  Q1 ██ 92% … Q4 █ 38% ⚠ hardest       │
│  [⬇ Export XLSX] [⬇ PDF] [📧 Send results] [Run again ▶]     │
└──────────────────────────────────────────────────────────────┘
```

---

### J3 — Participant: phone in one hand
**Flow:** `QR/code → Join (see WHAT you're joining) → Lobby → Question → Locked in → Reveal → (Leaderboard) → … → Finale`
**Items:** P0-2, P0-3, P1-4, P1-5, P1-6, P1-10 (non-MCQ types), P1-12 (join page), P4-1, P4-2.
**Invariants:** one thing per screen · thumb-reach targets · never a dead end · score/identity survives refresh.

```
 J3a JOIN              J3b LOBBY             J3c QUESTION
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Class 7     │      │ You're in! ✓ │      │ Q3/6    ⏱◔18 │
│  Maths       │      │              │      │ Capital of   │
│  Live Quiz · │      │ 46 others    │      │ France?      │
│  host: Demo  │      │ here 👥      │      │ ┌──────────┐ │
│              │      │              │      │ │ A London │ │
│ Your name    │      │ Starting     │      │ │ B Paris  │ │
│ [Brave Falcon│      │ soon…        │      │ │ C Berlin │ │
│  🎲 reroll ] │      │ 😄🔥👏 react  │      │ │ D Madrid │ │
│ [ JOIN ▶ ]   │      │              │      │ └──────────┘ │
└──────────────┘      └──────────────┘      │ tap = lock in│
                                            └──────────────┘
 J3d LOCKED IN         J3e REVEAL            J3f FINALE
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│      ⚡       │      │ ✓ Correct!   │      │   🎉 #2 🎉   │
│  Locked in!  │      │   +870 pts   │      │ Brave Falcon │
│  3rd fastest │      │ ✅ B Paris 61%│      │ 4/6 correct  │
│              │      │ ▒ A 12 ▒ C 15│      │ fastest: Q2  │
│ waiting for  │      │              │      │──────────────│
│ the reveal…  │      │ You: #4 ▲2   │      │ Make your own│
│  ▂▃▅▆ 39/47  │      │ ────────────│      │ quiz — free  │
└──────────────┘      │ next in 5…4… │      │ [Try Swaya ▶]│
                      └──────────────┘      └──────────────┘
```
Reveal rules (fixes P0-2): **your** pick = green ✓ if right / red ✗ if wrong; the correct option is always highlighted green for everyone; bars animate in. Host Stop at any point → J3f within 1 s (P1-8) or ≤3 s (P0-3 polling), never "Waiting…".

---

### J4 — Test candidate: under pressure, kept oriented
**Flow:** `link/e/:slug → Entry (rules up front) → Q1…Qn (palette, flag, autosave) → Submit confirm → Score → results email later`
**Items:** P3-6, P3-5 (host side), P1-9.

```
 J4a ENTRY                    J4b QUESTION
┌────────────────────┐       ┌────────────────────────┐
│ Python Screening   │       │ ⏱ 41:32 left   Q7/20   │
│ 20 questions · 45m │       │ [1][2][3][4][5][6][●7] │
│ closes Fri 18:00   │       │ [8]…[20]  ⚑2 flagged   │
│ ────────────────── │       │                        │
│ ✓ +1 correct       │       │ What does `yield` do?  │
│ ✓ no negative      │       │ ○ returns & exits      │
│ ⚠ timer per quest. │       │ ● pauses generator     │
│ 📷 webcam snapshots│       │ ○ raises StopIteration │
│                    │       │ ○ none of these        │
│ Name  [________]   │       │ ✓ saved · [⚑ Flag]     │
│ Email [________]   │       │ [← Back]      [Next →] │
│ [ Start test ▶ ]   │       └────────────────────────┘
└────────────────────┘
 J4c SUBMIT                   J4d DONE
┌────────────────────┐       ┌────────────────────────┐
│ Submit 20 answers? │       │      🏆 Submitted      │
│ 2 flagged, 1 blank │       │   Your score: 17/20    │
│ [Review] [Submit ✓]│       │ Detailed results will  │
└────────────────────┘       │ be emailed by the host.│
                             │ [Create your own free] │
                             └────────────────────────┘
```

---

### J5 — Organizer: proving what happened
**Flow:** `Results (sidebar) → filter by mode/date → Session recap / Test results → per-candidate Integrity report → export/send`
**Items:** P3-4, P3-5, P1-6, X-1.

```
 J5a RESULTS HUB                          J5b INTEGRITY REPORT (per candidate)
┌─────────────────────────────────────┐  ┌─────────────────────────────────┐
│ Results        [All ▾][This month ▾]│  │ ← Test results   Ria Sharma     │
│ ─────────────────────────────────── │  │ Score 17/20 · Integrity 92 ⚠1   │
│ ⚡ Class 7 Maths   today   47 ppl    │  │ ───────────────────────────────│
│    78% correct      [Recap →]       │  │ Snapshot timeline               │
│ 🎯 Python Screening  Wed   31 cand. │  │ [📷][📷][📷][⚠📷][📷][📷]        │
│    avg 14.2/20      [Results →]     │  │  0:00      12:40 two faces      │
│ 🤝 Town Hall pulse   Mon   210 resp │  │ Violations: 1 · tab blur 0      │
│    [Responses →]                    │  │ Adj. score 15.6 → rank #4 (▼1)  │
│ 📋 Feedback survey   open  58 resp  │  │ [⬇ PDF] [Accept] [Flag review]  │
└─────────────────────────────────────┘  └─────────────────────────────────┘
```

---

### J6 — Survey respondent (async link)
**Flow:** `link/poll/:slug → all questions, one screen per question or scrollable form → Thanks`
**Items:** P3-8 (mode-aware chrome), P2-1 naming.

```
┌──────────────────┐      ┌──────────────────┐
│ Feedback Survey  │      │  ✓ Thank you!    │
│ 5 questions ·2min│      │ Your response is │
│ anonymous        │      │ recorded.        │
│ ──────────────── │  ──► │                  │
│ 1. Rate today ★★★│      │ Powered by Swaya │
│ 2. One word… [__]│      │ [Make your own]  │
│ [Submit ▶]       │      └──────────────────┘
└──────────────────┘
```

### Blueprint → work-item map

| Blueprint | Screens | Built by |
|---|---|---|
| J1 host creation | Home, intent chooser, builder+preview | P2-2, P2-3, P2-4, P2-8 |
| J2 host live | lobby, question cockpit, projector, stop/recap | P0-1, P1-1…P1-7, P1-9, P1-11, P3-9 |
| J3 participant | join, lobby, question, reveal, finale | P0-2, P0-3, P1-4…P1-6, P1-10, P1-12, P4-1, P4-2 |
| J4 candidate | entry, palette, submit, done | P3-6, P1-9 |
| J5 organizer | results hub, recap, integrity report | P3-4, P3-5, P1-6 |
| J6 respondent | survey, thanks | P3-8, P2-1 |

---

## P0 — Trust: fix what breaks live rooms

> Review §3 bugs 1–4 + archive. Ship as one release. Highest urgency: every live session is exposed to these today.

### P0-1 ✅ Control room rehydrates join code/URL on reload or reattach
- **Bug:** With a session already running, `/quiz/:id/control` renders `Join URL: …/join/undefined`, `Join Code: 0`, and a QR encoding the bad URL (review §3.1; reproduced on sessions 1842/1844).
- **Fix:** On control-room mount, fetch the active session (`GET /quizzes/{id}/sessions`, status ≠ ended) and hydrate `join_code`/URL/QR from the server instead of relying on the in-memory response of the local "Start Session" action. Same for participant count and status.
- **Files:** `frontend/src/features/quiz/QuizControl.jsx`; verify `GET /quizzes/{id}/sessions` returns `join_code` per session (extend `backend/features/quiz/session_service_async.py` + `schemas.py` if not).
- **Accept:** Start session → hard-refresh control room → code/URL/QR correct. Open control from second tab → correct. Selenium check added.
- **Size:** S

### P0-2 ✅ Participant reveal: correct answer must look correct
- **Bug:** Participant's selected option always gets red border + ✗ icon, even when correct (review §3.2, screenshot `a03`). Scoring is right; presentation is wrong.
- **Fix:** In the answered/reveal state, style selection by correctness: green + ✓ when correct, red + ✗ when wrong, and highlight the correct option for everyone after reveal. Add "+N pts" confirmation.
- **Files:** `frontend/src/features/audience/AudienceSession.jsx` (+ its CSS).
- **Accept:** Selenium two-window run: correct answer shows green ✓; wrong answer shows red ✗ AND highlights the right option.
- **Size:** S

### P0-3 ✅ Participants get an explicit session-ended state
- **Bug:** After host Stop, participants hang on "Waiting for next question…" forever (review §3.3, screenshot `a09`).
- **Fix:** Polling loop must detect `status: ended` and render an end screen: final score, rank, "Thanks for playing", CTA to swaya.me. (Full animated finale is P1-6; this is the minimal honest state.)
- **Files:** `frontend/src/features/audience/AudienceSession.jsx`; ensure session-status endpoint used by audience polling exposes `ended`.
- **Accept:** Host stops quiz → participant view switches to end screen within one polling cycle (≤3 s).
- **Size:** S

### P0-4 ✅ Fix 500 on deleting quizzes with exam sessions
- **Bug:** `DELETE /quizzes/{id}` → `IntegrityError: Column 'quiz_id' cannot be null` on `quiz_sessions` when exam responses exist (review §3.4).
- **Fix:** Make delete cascade explicit: delete (or soft-archive) dependent `quiz_sessions`, participants, answers in the service; or FK `ON DELETE CASCADE` via Alembic migration (`YYYYMMDD_HHMM_…` naming). Decide policy: hard-delete cascades for drafts/tests; recommend archive (P0-5) for anything with responses.
- **Files:** `backend/features/quiz/quiz_service_async.py`, `backend/persistence/models/quiz.py`, new Alembic migration.
- **Accept:** Delete temp exam **quiz 1001** on test (left over from the review) successfully; regression: delete quiz with live-quiz sessions, exam sessions, offline responses.
- **Size:** M

### P0-5 ✅ Archive action for activities (soft path)
- **Why:** Deleting data-bearing activities is destructive; dashboard noise needs a non-destructive exit (review §3.7, §4.3).
- **Fix:** `archived_at` column on Quiz + "Archive"/"Unarchive" actions; archived items excluded from default lists and stat counts, visible via filter.
- **Files:** migration, `quiz_service_async.py`, routes, `Dashboard.jsx` table actions, locales (11 files).
- **Accept:** Archive hides from table + counts; filter shows; unarchive restores.
- **Size:** M

---

## P1 — The live loop: host cockpit + participant game

> Review §4.4, §4.5, §4.9. The highest-impact redesign. Target: a host never scrolls mid-session; a participant gets a real finale.

### P1-1 ✅ Control room two-pane cockpit layout
- Replace the long scrolling page with: left **Stage pane** (mirrors Present view), right **Control rail** (LIVE timer, joined/answered counts, big Next, Back, Leaderboard toggle, Present F5, Stop). No vertical scrolling at 1366×768. Footer/legal links removed from this route.
- **Files:** `QuizControl.jsx` (major refactor — consider splitting `ControlRail.jsx`, `StagePane.jsx`), `QuizPresent.jsx` (share stage component), themes CSS.
- **Accept:** All session controls visible without scroll; Space advances; existing Selenium flows pass without `scrollIntoView`.
- **Size:** XL

### P1-2 ✅ Join code pinned & huge during the entire session
- Persistent join bar on the stage pane (code + QR popover + copy link) in lobby AND mid-question. Depends on P0-1.
- **Accept:** Code legible from screenshot at every session state.
- **Size:** S (within P1-1)

### P1-3 ✅ "N answered / M joined" live counter next to Next
- Host's advance decision needs response progress (review §4.4). Backend already aggregates response counts; expose per-current-question answered count in the host polling payload.
- **Files:** `session_service_async.py`, `QuizControl.jsx`.
- **Accept:** Counter updates while participants answer (Selenium two-window test).
- **Size:** M

### P1-4 ✅ Pre-session lobby moment
- Names pop in as they join (host side), participant lobby shows "You're in — N others here" + activity title/host instead of bare spinner. Optional warm-up toggle (emoji wall) — stretch, may defer.
- **Files:** `QuizControl.jsx`, `AudienceSession.jsx`.
- **Size:** M

### P1-5 ✅ Participant reveal & leaderboard moments
- Animated bar fills, +points count-up, rank delta ("▲ 2 places"), podium screen for top-3 when host shows leaderboard, "you" row always pinned. Builds on P0-2.
- **Split (sonnet-review §4):** **P1-5a** — static reveal/leaderboard states, self-contained, no animation dependency. **P1-5b** — animations, depends on the **P3-1a motion library** (pulled forward into M2; full token unification stays P3-1b/M4).
- **Files:** `AudienceSession.jsx` + CSS/motion utilities (keyframe library delivered by P3-1a).
- **Size:** L

### P1-6 ✅ Session finale screens (participant + host recap)
- Participant: confetti for top 3, personal summary (score, accuracy, fastest answer), conversion CTA. Host: auto-navigate on Stop to a recap (podium, per-question accuracy, hardest question, export buttons) instead of staying on a dead control page; recap also reachable from History.
- **Files:** `AudienceSession.jsx`, new `SessionRecap.jsx`, route `/quiz/:id/recap/:sessionId`, `QuizControl.jsx` stop handler, `QuizHistory.jsx` links.
- **Size:** L

### P1-7 ✅ Stop Quiz confirmation UX
- Move confirm next to the (now fixed-position) Stop control; copy reassures "Results are saved to History"; primary button reachable by keyboard (review §3.8).
- **Size:** S

### P1-8 ✅ WebSocket/SSE channel for session state (behind a flag)
- Replace 2–3 s polling for: question advance, reveal, leaderboard toggle, session end, answered-count (review §4.9). Use Redis pub/sub fan-out; SSE is acceptable v1 (simpler through nginx). Keep polling as automatic fallback. Feature-flag per session.
- **Files:** new `backend/broker/api/session_events.py` (SSE endpoint), `session_service_async.py` publish hooks, frontend `useSessionChannel` hook used by `AudienceSession.jsx`/`QuizControl.jsx`/`QuizPresent.jsx`.
- **Subtask P1-8a (prerequisite, sonnet-review §10):** nginx SSE config — `proxy_buffering off`, `proxy_cache off`, long `proxy_read_timeout`, `X-Accel-Buffering: no` on the SSE location for **test.swaya.me first**; same change staged for live during promote. **Accept:** events arrive < 500 ms on test.swaya.me before any frontend SSE work is considered done (nginx silently buffers SSE otherwise — this is the first failure mode).
- **Accept:** Advance→participant render < 1 s on test; fallback engages when SSE blocked; load-test with locust (existing tooling) at 500 participants.
- **Size:** XL

### P1-9 ✅ Server-authoritative timers
- Countdown derived from server `question_started_at + max_time_seconds` (single clock), not client `setInterval` drift (review §4.9). Host, participant, and present views agree within ~250 ms.
- **Files:** session schemas (expose timestamps), the three session views.
- **Size:** M

### P1-10 ✅ Participant UX for non-MCQ question types
- **Gap (sonnet-review §1):** J3 and P0-2/P1-5 only cover MCQ. Live polls run `word_cloud`, `scale`, `single_line`, `paragraph`, `one_word` — each needs its own answer UI and a defined "reveal" state (e.g., word cloud: your word highlighted in the aggregate cloud; scale: your pick marked on the distribution; open text: "response recorded" + optional aggregate view). No leaderboard/points framing for poll types.
- **Files:** `AudienceSession.jsx` (per-type answer + reveal components), participant CSS; verify reveal payloads per type in `session_service_async.py`.
- **Accept:** Selenium two-window run per question type: answer submits, locked-in state shown, reveal state is type-appropriate (never the MCQ green/red treatment on a word cloud).
- **Size:** L

### P1-11 ✅ Presenter/projector view (`/present/:id`) redesign
- **Gap (sonnet-review §2):** referenced by J2 (`Present F5`) and P1-1 file list but never scoped. Distinct concerns from control room: legible from 5 m (type scale), high contrast, join code + QR persistently huge, animated bar fills, fullscreen toggle, no login required, no admin chrome.
- **Files:** `QuizPresent.jsx` (consume the shared stage component from P1-1), themes CSS.
- **Accept:** noVNC screenshot at 1920×1080: question + options + join code readable when downscaled to 25 %; reveals animate; works logged-out.
- **Size:** M

### P1-12 ✅ Join page redesign (`/join`)
- **Gap (sonnet-review §3):** J3a is unowned — P1-4 starts at the post-join lobby. The join form must show *what* you're joining once a code resolves (activity title, mode chip, host name) and offer a suggested anonymous name with 🎲 reroll before committing. Mode-aware copy (no "Join Quiz" for polls — overlaps P3-8).
- **Files:** `frontend/src/features/audience/` join component, backend join-code lookup to return title/mode/host pre-join, locales.
- **Accept:** Enter valid code → title/mode/host render before joining; reroll changes suggested name; invalid code shows a friendly inline error.
- **Size:** M

---

## P2 — The shop window: home, create, templates

> Review §3.6, §3.7, §4.2, §4.3, §4.7.

### P2-1 ✅ Mode renames across product: Live Quiz / Live Poll / Survey / Test
- `quiz → Live Quiz`, `poll → Live Poll`, `offline_poll → Survey`, `exam → Test` — display names only (DB enums unchanged). All UI chrome, tags, create cards, builder, results + all 11 locale files. The i18n pipeline from the home.v2 work applies.
- **Accept:** No user-visible "Online Quiz"/"Online Poll"/"Offline Poll" strings remain (grep locales + Selenium text dumps).
- **Size:** M

### P2-2 ✅ Intent-first Create flow
- One primary "Create" → triad chooser using landing language ("I want energy / honesty / it counts" → Live Quiz / Live Poll / Test, with Survey as the async variant under honesty). Direct cards remain below for power users (review §4.7).
- **Files:** `Dashboard.jsx`, new `CreateChooser.jsx`, locales.
- **Size:** M

### P2-3 ✅ AI generation as the hero of creation
- "Describe your session → draft" step: topic, audience, question count, difficulty, language (leverage 11 locales). Surfaces the existing Generate-with-AI capability at the entry point instead of mid-builder (review §4.7).
- **Files:** `QuizBuilder.jsx` (extract generation panel), `CreateChooser.jsx`, backend generation endpoint review for these params.
- **Size:** L

### P2-4 ✅ Home redesign (time-based, not table-based)
- Keep hero + create cards. Add: **Up next** strip (ready/scheduled, one-click Run / Copy link / QR), **Continue editing** (3 recent drafts), **Last session** recap card. Move the full table to a new **Activities** page (P2-5). Stat tiles count meaningful things (sessions this week, participants, avg score) — not raw rows (review §4.3).
- **Files:** `Dashboard.jsx` split into `Home.jsx` + components; new backend aggregate endpoint for home stats.
- **Size:** XL

### P2-5 ✅ Activities page: archive, bulk actions, filters, sort
- Full table with: archived filter (P0-5), bulk archive/delete/assign-folder, sort by last-run/created, "needs attention" filter (0-question drafts, expired-but-published tests), search. Folder tree stays in sidebar.
- **Files:** new `features/activities/Activities.jsx`, route + sidebar entry, backend list params (sort, archived, attention flags).
- **Size:** L

### P2-6 ✅ Sidebar IA: Home · Activities · Results · Settings
- Restructure ProLayout routes (review §4.2): Results becomes first-class (P3-4); admin stays in avatar menu; remove GitHub icon + BETA badge from authed app header; tier badge moves into account dropdown (review §4.8).
- **Files:** `App.jsx`, locales.
- **Size:** M

### P2-7 ✅ Template gallery
- Replace the one-row modal table with a browsable gallery page (cards: preview, category, question count, usage count, mode chip). Seed 20–30 quality templates across classroom / all-hands / training / hiring verticals (content task — track separately per vertical if needed).
- **Files:** new `features/templates/TemplateGallery.jsx`, backend `template-library` endpoint extension (category, usage stats), seed script.
- **Size:** L

### P2-8 ✅ Builder ergonomics
- Single-column inline question editing with live phone-frame participant preview on the right; drag-reorder (API exists: `questions/reorder`); duplicate question; one-click "Unpublish & edit → republish" prompt replacing the yellow read-only banner; surface Excel import/export (exists) in the builder toolbar (review §4.7).
- **Files:** `QuizBuilder.jsx` (major), new `ParticipantPreview.jsx`.
- **Size:** XL

---

## P3 — Coherence: design system + results hub

> Review §4.6, §4.8.

### P3-1 ⬜ Design tokens & motion system unification
- Single `--sw-*` scale (color/type/space/radius/shadow/motion durations) consumed by landing, app, participant, and present surfaces — today four dialects (review §4.8). Document in `frontend/src/themes/README.md`.
- **Split (sonnet-review §4):** **P3-1a** — standalone keyframe/motion utility library (bar fill, count-up, rank shuffle, confetti), shipped in **M2** so P1-5b/P1-6 aren't blocked. **P3-1b** — full token unification across the four surfaces, stays **M4**.
- **Size:** L (P3-1a: S, P3-1b: L)

### P3-2 ⬜ Mode accent colors carried through
- One accent hue per mode (as on landing chips) applied across builder, control room, participant, results — "the room knows what game it's playing".
- **Files:** `themes/themes.js` + per-mode accent var, components.
- **Size:** M

### P3-3 ⬜ Typography pairing
- Landing's display serif for headline moments (participant score reveal, podium, recap headings); existing sans for UI. Webfont subsetting for participant page weight budget.
- **Size:** S

### P3-4 ⬜ Unified Results hub
- New **Results** area listing all past sessions/surveys/tests across activities (filterable by mode/date/folder), deep-linking to session recap (P1-6), survey responses, exam results. Replaces hunting through per-quiz History buttons (review §4.2, §4.6).
- **Files:** new `features/results/ResultsHub.jsx`, backend cross-quiz sessions listing endpoint, sidebar (P2-6).
- **Size:** L

### P3-5 ⬜ Exam: per-candidate Integrity report view
- Dedicated sober page per candidate: webcam snapshots timeline, violations, integrity score derivation, adjusted rank explanation — replacing horizontal-scroll table columns (review §4.6).
- **Files:** `ExamResults.jsx` + new `IntegrityReport.jsx`, backend detail endpoint (data exists).
- **Size:** L

### P3-6 ⬜ Test candidate experience polish
- Question palette/progress ("3 of 20, 2 flagged"), flag-for-review, autosave indicator, low-time urgency styling, post-submit "what happens next" (results email timing). Revisit "no going back" — either per-question setting or clearly warned (review §4.6).
- **Files:** `ExamSession.jsx`, exam settings in builder, backend exam config.
- **Size:** L

### P3-7 ⬜ Session skins v1 (host-chosen, participant-visible)
- Reframe themes: host's admin chrome gets light/dark only; **skins** (Classroom, Boardroom — mockups exist in repo —, Party) style what participants and the projector see, chosen per activity. Builds on existing themes.js registry + Boardroom mockup commit `a254a27`.
- **Files:** `themes/`, `AudienceSession.jsx`, `QuizPresent.jsx`, builder setting, migration for `skin` column.
- **Size:** XL

### P3-8 ✅ Copy & chrome cleanup sweep
- "1 Questions" pluralization; "0 (0.0%)" noise on reveals; `/join` says "Join Quiz" for polls (make mode-aware or neutral "Join Session" — join page itself is redesigned in P1-12); exam entry close-time formatting/wrapping; disabled Submit button lingering after submit; footer links out of session routes (if not already via P1-1). All 11 locales (review §3.10).
- **Size:** M

### P3-9 ⬜ Live poll results visualization (host stage + projector)
- **Gap (sonnet-review §11):** word cloud and scale results render mid-session on the control stage and `/present` but have no owned design. Scope: word-cloud layout that stays legible as it grows, scale/NPS distribution histogram, live-updating response count for open-text types, real-time update path (polling now, P1-8 SSE when flagged). P3-2 accent colors apply but don't cover the visualization itself.
- **Files:** shared stage component (P1-1), `QuizPresent.jsx`, results components, themes CSS.
- **Accept:** Selenium poll run with ≥10 word-cloud answers: cloud legible on projector screenshot; scale question shows distribution, not raw rows.
- **Size:** M

---

## P4 — Reach

> Review §4.5.7, §5 P4.

### P4-1 ⬜ Participant PWA + wake lock
- Installable manifest, service worker for shell caching, screen wake lock during sessions.
- **Size:** M

### P4-2 ⬜ Reconnect-resilient participant sessions
- Session token survives refresh/network blip/phone lock; auto-rejoin with same identity and score. (Pairs with P1-8 reconnect logic.)
- **Accept:** Selenium: join → reload mid-question → same name/rank, current question shown.
- **Size:** M

### P4-3 ⬜ Self-serve plan upgrades
- Plans page ends in "email us" today (review §2, §4.3). Integrate payment provider chosen in **P4-7**, tier change flow on existing TierService/Redis enforcement. **Note:** JWT tier-stale bug memory — coordinate with the post-2026-06-01 fix. **Blocked by P4-7.**
- **Size:** XL

### P4-4 ⬜ Public quiz discovery (explore page)
- Browse/run public templates without an account beyond join codes. Scope deliberately small: curated global templates only.
- **Size:** L

### P4-5 ⬜ Team workspaces
- Shared folders/activities within a tenant using existing tenant/role model (admin/user/viewer); "shared with me" view.
- **Size:** XL

### P4-6 ⬜ Production landing parity (deploy action)
- **Scope (clarified per sonnet-review §9):** promote the **existing test.swaya.me landing** ("One room. Every voice.") to production **as-is, after P0 — without waiting for P2-4**. The P2-4 home redesign ships later through the normal promote flow as part of M3; it is *not* part of this item. Accepted trade-off: landing and logged-in dashboard will be visually out of step between M1 and M3.
- **Size:** S (deploy + verify)

### P4-7 ⬜ Decide payment provider (Razorpay vs Stripe)
- **Gap (sonnet-review §8):** decision was an inline note inside P4-3 but blocks its design entirely. Evaluate: Indian vs global audience split, fee structure, webhook reliability, subscription/tier-change APIs, integration surface with TierService/Redis. Output: a one-page decision record in `specs/backend/`.
- **Accept:** decision documented and approved; P4-3 unblocked.
- **Size:** S

---

## X — Cross-cutting

### X-1 ⬜ Metrics instrumentation
- Events for the review's success metrics: participant rejoin rate, host-never-scrolls/never-loses-code (control-room error + scroll telemetry), finale→signup conversion, time-to-first-published-activity, weekly active hosts (review §5). Minimal: backend event table + lightweight frontend beacon; admin Statistics page chart additions.
- **Size:** L

### X-2 ⬜ Journey smoke-test suite from exploration scripts
- Promote `scripts/fable_explore_1–5.py` into maintained `scripts/smoke/` suite: login, create→publish→delete, live two-window session (join code, correct/incorrect reveal, leaderboard, end-state), exam end-to-end, poll question types. Run against test before every promote-live.
- **Size:** M

### X-3 ⬜ Test-data cleanup on test env
- After P0-4: delete leftover **quiz 1001** ("Fable Review Temp Exam"); archive/delete regression debris ("Proctoring Regression Exam …" ×40, "nnnnnnnnn", "b", etc.) so dashboards reflect reality during dogfooding.
- **Size:** S

### X-4 ⬜ Accessibility pass on participant + exam surfaces
- Keyboard answerable, focus states, ARIA on options/timer, color-contrast check of reveal states (esp. new green/red), reduced-motion respect for P1-5/P1-6 animations.
- **Size:** M

### X-5 ⬜ Spec docs for architecture changes + new API endpoints
- Write `specs/architecture/session-events.md` (SSE/WS design, fallback, scaling) and `specs/frontend/design-tokens.md` before starting P1-8 / P3-1.
- **Extended (sonnet-review §6):** one-page API spec (request params, response schema, auth) for each new endpoint **before** dependent frontend work starts: home stats aggregate (P2-4), cross-quiz sessions listing (P3-4), per-candidate integrity detail (P3-5), pre-join code lookup (P1-12). Place in `specs/backend/`.
- **Size:** M

### X-6 ⬜ Template content seeding
- **Gap (sonnet-review §7):** P2-7 deferred content "to track separately" — nothing tracked it; the gallery would ship empty. Seed minimum **8–10 templates across all four modes** to open the gallery (hard dependency for P2-7 go-live), growing to 20–30 across classroom / all-hands / training / hiring verticals. Localized titles/descriptions where feasible.
- **Files:** seed script (per P2-7 backend), template content (Markdown/Excel via existing import).
- **Accept:** gallery shows ≥8 quality templates at P2-7 launch; each runnable end-to-end.
- **Size:** M (content-heavy)

---

## Sequencing & dependencies

```
P0-1 ──► P1-2
P0-2 ──► P1-5a ──► P1-5b ──► P1-6
P0-3 ──► P1-6
P0-4 ──► X-3
P0-5 ──► P2-5
P1-1 ──► P1-2, P1-3, P1-7, P1-11 (shared stage), P3-9
P1-8a (nginx) ──► P1-8 ◄── X-5     P1-8 ──► P4-2 (reconnect), P1-3 (live counts ideal)
P1-12 ◄── X-5 (pre-join lookup spec)
P2-4 ──► P2-5, P2-6        P2-4 ◄── X-5 (stats endpoint spec)
P2-6 ──► P3-4              P3-4, P3-5 ◄── X-5 (endpoint specs)
P3-1a (motion lib, M2) ──► P1-5b, P1-6
P3-1b (tokens, M4) ──► P3-2, P3-3, P3-7
P4-7 ──► P4-3
X-6 ──► P2-7 (gallery go-live)
P0 (all) ──► P4-6 (prod landing promote — explicitly does NOT wait for P2-4)
```

**Suggested milestones**
1. **M1 (P0 complete):** live rooms trustworthy → promote to prod + P4-6 landing parity.
2. **M2 (P1-1…P1-7, P1-10…P1-12, **P3-1a** motion lib):** cockpit + participant game (all question types, join page, projector) on prod; P1-8/P1-9 behind flag on test.
3. **M3 (P2 complete + X-6 content):** new home/create/templates; mode renames.
4. **M4 (P3 complete incl. P3-1b tokens, P3-9):** unified look & feel + Results hub.
5. **M5 (P4 selective):** PWA + reconnect first; payments after P4-7 decision and when business-ready.

---

## Verification protocol (every item)

1. Implement → `npm run build` in `frontend/` (and backend restart for API changes).
2. Deploy to **test** only; never touch live without explicit human confirmation.
3. Run the relevant smoke script (X-2 suite) + manual noVNC spot-check (http://www.swaya.me:7900).
4. Mark item 🟨, request review; on approval `./deploy.sh promote-live`, mark ✅.

## Change log

| Date | Item | Change |
|---|---|---|
| 2026-06-11 | — | Plan created from fable_review.md |
| 2026-06-12 | — | Gap fixes from [`sonnet-review.md`](./sonnet-review.md): added P1-10 (non-MCQ participant UX), P1-11 (projector view), P1-12 (join page), P3-9 (poll visualizations), P4-7 (payment provider decision), X-6 (template seeding); split P3-1→a/b and P1-5→a/b to resolve M2/M4 conflict; P1-8a nginx SSE prerequisite; X-5 extended to new API endpoint specs; P4-6 scope clarified; i18n added to Definition of Done; sequencing + milestones updated. Total 41→47 items. |
