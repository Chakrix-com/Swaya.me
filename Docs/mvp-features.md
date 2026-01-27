# MVP Feature List — Quiz-First

## Objective

Define the minimum set of features required to deliver an
end-to-end, usable **Interactive Quiz experience** for live audiences,
while preserving architectural integrity and future extensibility.

This MVP is intentionally narrow and focuses on **value delivery**, not
feature completeness.

---

## MVP Scope Summary

The MVP enables:
- A host to create and run a live quiz
- An audience to join and participate in real time
- A visible outcome (results) that demonstrates engagement value

Anything not directly supporting this outcome is **out of scope**.

---

## Core MVP Feature: Live Quizzes

| Category | Primary Actor | Feature | Description | Example (Optional) | In-Scope | Out-of-Scope |
|--------|---------------|---------|-------------|--------------------|---------|--------------|
| Quiz Authoring | Host | Create quiz | Create a logical container for a quiz session | “Weekly Science Quiz” | Create quiz with title | Templates, folders |
| Quiz Authoring | Host | Add question | Add a question to a quiz | MCQ: “2+2=?” | Single-choice question | Multi-select, media |
| Quiz Authoring | Host | Define correct answer | Mark the correct option for a question | Option B | One correct answer | Partial scoring |
| Quiz Authoring | Host | Save quiz | Persist quiz for reuse | Reuse later | Basic persistence | Versioning |
| Quiz Session Control | Host | Start quiz | Start a live quiz session | Click “Start” | Manual start | Scheduling |
| Quiz Session Control | Host | Advance question | Move quiz to next question | Click “Next” | Sequential flow | Back/skip |
| Quiz Session Control | Host | End quiz | End the active quiz session | Click “End” | Manual end | Auto-end |
| Audience Participation | Audience | Join quiz | Join an active quiz session | Code / link | Anonymous join | Login required |
| Audience Participation | Audience | View question | See the currently active question | Live display | Real-time view | Question history |
| Audience Participation | Audience | Submit answer | Submit answer to active question | Select option | One submission | Answer change |
| Audience Participation | Audience | Submission feedback | Acknowledge answer submission | Tick / message | Confirmation | Rankings |
| Live Results | Platform | Aggregate answers | Aggregate responses per option | Count / % | Basic aggregation | Weighting |
| Live Results | Audience | View correct answer | Reveal correct option | After question | Reveal once | Leaderboards |
| Live Results | Host | View response summary | View live answer distribution | Bar / count | Live counts | Advanced analytics |
| Realtime | Platform | Broadcast question | Push question to participants | Live push | Near real-time | Offline sync |
| Realtime | Platform | Broadcast results | Push result updates | Live update | Near real-time | Guaranteed ordering |
| Tenant Context | Platform | Resolve tenant | Resolve runtime tenant context | Single tenant | Single-tenant | Tenant admin |
| Security | Platform | Protect host actions | Restrict host-only operations | Auth required | Simple auth | SSO, MFA |
| Security | Platform | Scope audience access | Restrict access to session | Session-bound | Session scope | Roles |
| Observability | Platform | Track interactions | Count submissions/events | Metric count | Conceptual metrics | Billing |
| Testability | Platform | Isolate quiz feature | Allow independent testing | Mock realtime | Feature-level tests | Full E2E |

