# Gap Analysis: fable-implementation-plan.md

**Reviewer:** Claude Sonnet 4.6  
**Source plan:** [`specs/fable-implementation-plan.md`](./fable-implementation-plan.md)  
**Date:** 2026-06-12

Eleven gaps identified, grouped by severity.

---

## 1. Participant journey for non-MCQ questions — entirely missing

J3 only shows MCQ answer options. Live polls use `word_cloud`, `scale`, `single_line`, `paragraph`, and `one_word` question types — each with a completely different participant UI. None of P1-4/P1-5/P0-2 call this out, and there is no work item scoping what "correct participant reveal" even means for a word cloud or scale question. This is a significant coverage gap given polls are a primary mode.

**Recommendation:** Add a work item under P1 (or extend P1-5) explicitly scoping participant UX for each non-MCQ type, including what the reveal state looks like for word cloud aggregates and scale distributions.

---

## 2. Presenter/projector view (`/present/:id`) has no owned work item

`QuizPresent.jsx` is listed as a file in P1-1, and J2 wireframes reference `[⬛ Present F5]`, but there is no work item that scopes what the projector view should look like, who it is for, or what improvements it needs. It has its own font-size/contrast/no-login concerns distinct from the control room.

**Recommendation:** Add a dedicated P1 item for the projector/presenter view: large-text question display, bar fill animation visible from 5 m, no-login requirement, full-screen toggle. Reference both `QuizPresent.jsx` and the stage pane component shared with P1-1.

---

## 3. The join page has no explicit work item

J3a shows a redesigned join screen (activity title, type, host, suggested anonymous names, reroll) but no work item targets it directly. P1-4 is titled "Pre-session lobby moment" and focuses on the post-join lobby. The join form itself — one of the highest-frequency participant entry points — falls through the cracks between P0 and P1.

**Recommendation:** Add a P1 item for the `/join` page: show activity name, mode, host name, and name suggestion with reroll before the participant commits. This is the first screen most participants ever see and is currently generic.

---

## 4. Milestone conflict: P3-1 is a dependency of P1-5 but scheduled two milestones later

The dependency graph states `P3-1 → P1-5` (motion/keyframe library from design tokens needed for participant reveal animations). P1-5 is in M2; P3-1 is in M4. As written, M2 cannot be completed.

**Recommendation:** Either split P3-1 into a "motion utilities only" subtask pulled into M2 (the full token unification can stay M4), or explicitly split P1-5 into P1-5a (basic non-animated reveal, self-contained) and P1-5b (animated bars + count-up, depends on P3-1). Update the sequencing diagram accordingly.

---

## 5. i18n work is not itemized for new screens

P2-1 and P3-8 call out the 11 locale files explicitly, but all new components — `CreateChooser`, `SessionRecap`, `IntegrityReport`, `ResultsHub`, `TemplateGallery`, the builder phone preview, and the join page redesign — will each need localization strings added. There is no umbrella item and no per-item callout. Untranslated chrome ships silently because no one owns it.

**Recommendation:** Either add an X-item for an i18n sweep (run after M3, cover all new keys introduced since P0) or add a checklist line to the Definition of Done: "all user-visible strings have locale keys in all 11 translation.json files."

---

## 6. New backend endpoints are mentioned but not spec'd

- P2-4 needs a home stats aggregate endpoint (sessions this week, participants, avg score)
- P3-4 needs a cross-quiz sessions listing endpoint (filterable by mode/date/folder)
- P3-5 needs a per-candidate detail endpoint (data "exists" but the shape is not defined)

Each is mentioned in passing under "Files" or Accept criteria. X-5 only covers two architecture docs (SSE, design tokens) — these new REST surfaces are unguarded. Without a schema, frontend and backend will diverge during implementation.

**Recommendation:** Extend X-5 to require a one-page API spec for each new endpoint (request params, response shape, auth) before the dependent frontend work starts. Or add a dedicated X item: "API spec sweep for P2-4, P3-4, P3-5 endpoints."

---

## 7. Template content seeding is deferred but not tracked

P2-7 states "Seed 20–30 quality templates — content task, track separately per vertical if needed." There is no X-item or placeholder for this. A template gallery page without templates is a dead page from day one.

**Recommendation:** Add an X-item for content seeding: assign per-vertical owners (classroom / all-hands / training / hiring), define the minimum set needed to open the gallery (suggest 8–10 across all modes), and mark it a hard dependency for P2-7 going live.

---

## 8. Payment provider decision is a prerequisite, not a work item

P4-3 flags "decision needed: Razorpay vs Stripe" inline but there is no `⬜ Decide payment provider` item. P4-3 is XL and cannot be designed — let alone implemented — without this decision. If it slips to implementation day it blocks the entire item.

**Recommendation:** Add a P4 prerequisite item: evaluate Razorpay vs Stripe (Indian vs global split, webhook support, TierService integration surface). Gate P4-3 on it explicitly in the sequencing diagram.

---

## 9. P4-6 scope is ambiguous

P4-6 ("promote test landing to production after P0, Size S") does not clarify *which* landing is being promoted — the current test.swaya.me one, or one that requires P2-4 (home redesign) first. Promoting an intermediate state could leave the landing and the dashboard visually inconsistent with each other.

**Recommendation:** Explicitly state what P4-6 promotes and what it does not. If it is "ship the existing test.swaya.me landing as-is, before P2-4," say so. If it waits for P2-4, update the dependency chain and milestone assignment. As written it is a deployment action masquerading as a feature item.

---

## 10. Nginx SSE configuration is a hidden P1-8 blocker

P1-8 has a parenthetical note about `proxy_buffering off` for SSE but it is not a tracked action. In practice, SSE through nginx silently buffers until the response is flushed or the connection is closed, which breaks the feature entirely on the test env. This is the first thing that will fail when P1-8 is implemented and it requires an nginx config change that may need a separate review.

**Recommendation:** Promote the nginx config change to an explicit numbered prerequisite or subtask under P1-8, with an acceptance criterion: verify SSE events arrive within 500 ms on test.swaya.me before any frontend work is considered done.

---

## 11. Poll results visualization during live sessions — no item

Live polls render word cloud and scale aggregates mid-session on the host stage and the projector. There is no work item for improving how these look on either surface. P3-2 adds mode accent colors but does not address the data visualization itself (word cloud layout, scale histogram, live-updating counts for open-text responses).

**Recommendation:** Add a P3 item (or extend P1-1) scoping the non-MCQ results display: what does a live word cloud look like on the presenter screen, what does a scale distribution show during a live poll, and how do these update in real time (polling vs. P1-8 SSE).

---

## Summary

| Gap | Severity | Easiest fix |
|---|---|---|
| 1. Non-MCQ participant UX | High — missing entire question-type coverage | New P1 item |
| 2. Projector view unowned | High — referenced but not scoped | New P1 item |
| 3. Join page unowned | High — first screen most users see | New P1 item |
| 4. P3-1 / P1-5 milestone conflict | High — M2 is undeliverable as written | Split P3-1 or P1-5 |
| 5. i18n not itemized for new screens | Medium — silently ships broken | Add to DoD or X-item |
| 6. New backend endpoints not spec'd | Medium — frontend/backend divergence risk | Extend X-5 |
| 7. Template content not tracked | Medium — gallery ships empty | New X-item |
| 8. Payment provider decision untracked | Medium — blocks XL item | New P4 prereq item |
| 9. P4-6 scope ambiguous | Low — confusing but not blocking | Clarify in prose |
| 10. Nginx SSE config untracked | Medium — first thing P1-8 will hit | Subtask under P1-8 |
| 11. Poll results visualization | Medium — missing coverage for poll mode | New P3 item or extend P1-1 |

The three most likely to cause mid-sprint collisions: **gap 4** (the milestone conflict will surface the moment P1-5 starts), **gap 1** (the first live-poll test will expose missing participant UX), and **gap 3** (the join page redesign implied by J3a has no owner).
