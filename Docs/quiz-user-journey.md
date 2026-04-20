# Quiz User Journey (MVP)

This document represents the end-to-end user journey for the
Quiz MVP using a lightweight, sequence-style swimlane format.

The intent is to clearly show:
- actor responsibilities
- interaction order
- realtime involvement

This representation is intentionally technology-agnostic.

---

## Actors

- Host: Creates and controls the quiz
- Platform: Orchestrates quiz lifecycle and state
- Realtime: Propagates live updates
- Audience: Joins and participates in the quiz

---

## Quiz Creation & Live Play Flow

```mermaid
sequenceDiagram
    participant Host
    participant Platform
    participant Realtime
    participant Audience

    Host->>Platform: Create Quiz
    Platform->>Platform: Persist Quiz

    Host->>Platform: Start Quiz
    Platform->>Platform: Generate Join Code

    Platform->>Realtime: Broadcast Question
    Realtime->>Audience: Push Question

    Audience->>Platform: Submit Answer
    Platform->>Platform: Record Answer
    Platform->>Platform: Aggregate Responses

    Platform->>Realtime: Broadcast Results
    Realtime->>Audience: Push Results

    Host->>Platform: End Quiz
    Platform->>Platform: Close Session
```
---

## Key Observations

- The **Host** controls quiz lifecycle (create, start, end)
- The **Platform** owns:
  - session state
  - answer aggregation
  - tenant resolution
- The **Realtime** layer is used only for:
  - broadcasting questions
  - pushing live updates
- The **Audience**:
  - joins anonymously
  - participates in real time
  - does not control flow

---

## Design Constraints (MVP)

- Happy path only
- No retry or reconnection logic
- No offline support
- No AI dependency
- Realtime failures should degrade gracefully

---

## Usage of This Document

- Input to high-level architecture design
- Reference for feature implementation
- Alignment artefact for contributors

This document will evolve incrementally as the platform grows.

---

## Exam Creation & Proctoring Flow (Host)

```mermaid
sequenceDiagram
    participant Host
    participant Builder as Exam Builder UI
    participant Platform
    participant DB

    Host->>Builder: Create new Exam (quiz_type=exam)
    Builder->>Platform: POST /quizzes/ {quiz_type: exam}
    Platform->>DB: Insert DRAFT quiz

    Host->>Builder: Add MCQ questions
    Builder->>Platform: POST /quizzes/{id}/questions (per question)

    Host->>Builder: Set exam dates, time limit, proctoring rules
    Note over Builder: Proctoring panel is above questions list<br/>Preset: Light / Standard / Maximum<br/>Escalation: lock after N violations

    Host->>Builder: Click "Save Settings"
    Builder->>Platform: PUT /quizzes/{id} {exam_start_at, exam_end_at, proctoring_policy}
    Note over Platform: Single call saves metadata + proctoring policy

    Host->>Builder: Click "Publish Exam"
    Builder->>Platform: POST /quizzes/{id}/publish-exam
    Platform->>DB: status=READY, generate exam_slug, create permanent session

    Host->>Host: Share /e/{slug} link
```

---

## Exam Participation Flow (with Proctoring)

```mermaid
sequenceDiagram
    participant P as Participant
    participant Gate as Proctoring Gate
    participant Exam as Exam Session
    participant Platform
    participant Proctoring as Proctoring Service

    P->>Platform: GET /e/{slug} — check exam status (open/upcoming/closed)
    P->>Platform: POST /e/{slug}/start {display_name}
    Platform-->>P: {session_token, questions, started_at (UTC+Z)}

    Note over Gate: ProctoringProvider fetches config<br/>GET /proctoring/config/{quiz_id}

    alt webcam_monitoring enabled (PRO+)
        Gate->>P: Request camera permission
        P->>Gate: Grant permission
        Gate->>Platform: POST /proctoring/session/webcam-granted
    end

    Gate->>Platform: POST /proctoring/session/init {webcam_granted, fingerprint}
    Platform->>Proctoring: Create proctoring_session row

    loop Answer questions
        P->>Exam: Select answer
        Exam->>Platform: POST /proctoring/answer-timing (speed check)
        Exam->>Platform: POST /e/{slug}/answer (autosave)

        alt Violation detected (tab switch, copy-paste, etc.)
            Proctoring->>Platform: POST /proctoring/event {rule_id, event_type}
            Platform->>Proctoring: Increment violation_count
            alt violation_count < lock_on_violation_count
                Platform-->>Exam: {is_locked: false, violations_remaining: N}
                Exam->>P: Show warning overlay (countdown)
            else violation_count >= lock_on_violation_count
                Platform-->>Exam: {is_locked: true}
                Exam->>P: Show lock screen (no more answers)
                alt auto_submit_on_lock
                    Platform->>Platform: Auto-submit participant's answers
                end
            end
        end
    end

    P->>Platform: POST /e/{slug}/submit
    Platform-->>P: {score, per-question breakdown}
```

---

## Live Exam Edit Flow (Host — Exam Already Published)

```mermaid
sequenceDiagram
    participant Host
    participant Builder as Exam Builder UI
    participant Platform

    Host->>Builder: Open /quiz/{id}/edit
    Builder->>Platform: GET /quizzes/{id}
    Note over Builder: status=ready → show yellow "exam is live" banner<br/>Questions list is locked (read-only)<br/>Proctoring settings and dates remain editable

    Host->>Builder: Change exam end date and adjust proctoring escalation threshold
    Host->>Builder: Click "Save Settings"
    Builder->>Platform: PUT /quizzes/{id} {exam_end_at, proctoring_policy}
    Note over Platform: Changes take effect immediately for active participants
```
