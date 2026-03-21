# Data Flow Diagrams

This document describes the key data flows for the Quiz MVP.

---

## Flow 1: Join Quiz (Audience)

### Description
An audience member joins an active quiz using a code or link, without requiring authentication.

### Actors
- Audience
- API Service
- Platform Kernel
- Database
- Live Session
- Realtime Hub

### Sequence

```mermaid
sequenceDiagram
  autonumber
  actor Audience
  participant UI as Audience UI
  participant API as API Service
  participant Platform as Platform Kernel
  participant DB as Database
  participant Session as Live Session
  participant Realtime as Realtime Hub

  Audience->>UI: Open join page (link / code / scan QR code)
  UI-->>Audience: Prompt for join code if required

  Audience->>UI: Submit join code
  UI->>API: Join request (code)

  API->>Platform: Join intent
  Platform->>Session: Resolve live session
  Session-->>Platform: Live session context

  Platform->>DB: Lookup quiz session
  DB-->>Platform: Session metadata (state, quiz reference)

  alt Session exists and ACTIVE
    Platform->>Platform: Create audience session (in-memory)
    Platform->>Realtime: Register participant for live updates
    Realtime-->>UI: Subscribed to live results
    UI-->>Audience: Waiting / lobby state
  else Session invalid or ENDED
    Platform-->>UI: Join rejected (invalid / ended)
    UI-->>Audience: Display error
  end
```

### Data Elements

**Request**:
```json
{
  "join_code": "ABC123"
}
```

**Response (Success)**:
```json
{
  "session_id": "sess_xyz",
  "participant_id": "part_123",
  "quiz_title": "Weekly Science Quiz",
  "status": "ACTIVE",
  "current_question": null
}
```

**Response (Error)**:
```json
{
  "error": "SESSION_NOT_FOUND",
  "message": "Quiz session not found or has ended"
}
```

---

## Flow 2: Submit Answer (Audience)

### Description
An audience member submits an answer to the currently active question.

### Sequence

```mermaid
sequenceDiagram
  autonumber
  actor Audience
  participant UI as Audience UI
  participant API as API Service
  participant Platform as Platform Kernel
  participant Quiz as Quiz Feature
  participant DB as Database
  participant Realtime as Realtime Hub

  Audience->>UI: View active question
  Audience->>UI: Select answer option
  UI->>API: Submit answer (session_id, participant_id, question_id, option_id)

  API->>Platform: Submit answer intent
  Platform->>Quiz: Validate and record answer

  Quiz->>Quiz: Check question state == OPEN
  Quiz->>Quiz: Check no prior submission

  alt Valid submission
    Quiz->>DB: Store answer submission
    DB-->>Quiz: OK
    Quiz-->>Platform: Answer recorded
    Platform-->>UI: Submission confirmed
    UI-->>Audience: Show confirmation
  else Invalid submission (late, duplicate, etc.)
    Quiz-->>Platform: Submission rejected
    Platform-->>UI: Rejection reason
    UI-->>Audience: Display error
  end

  Platform->>Realtime: Trigger answer aggregation update
  Realtime-->>UI: Broadcast updated counts
```

### Data Elements

**Request**:
```json
{
  "session_id": "sess_xyz",
  "participant_id": "part_123",
  "question_id": "q_456",
  "option_id": "opt_2"
}
```

**Response (Success)**:
```json
{
  "status": "recorded",
  "question_id": "q_456",
  "selected_option": "opt_2",
  "timestamp": "2026-01-27T10:30:45Z"
}
```

**Response (Error)**:
```json
{
  "error": "SUBMISSION_REJECTED",
  "reason": "QUESTION_CLOSED",
  "message": "Question is no longer accepting answers"
}
```

---

## Flow 3: Advance Question (Host)

### Description
Host advances the quiz to the next question.

### Sequence

```mermaid
sequenceDiagram
  autonumber
  actor Host
  participant UI as Host UI
  participant API as API Service
  participant Platform as Platform Kernel
  participant Quiz as Quiz Feature
  participant DB as Database
  participant Realtime as Realtime Hub

  Host->>UI: Click "Next Question"
  UI->>API: Advance question request (session_id)

  API->>Platform: Advance question intent
  Platform->>Quiz: Transition to next question

  Quiz->>Quiz: Close current question (if any)
  Quiz->>Quiz: Load next question
  Quiz->>Quiz: Set question state = OPEN

  Quiz->>DB: Update session state
  DB-->>Quiz: OK

  Quiz-->>Platform: Next question active
  Platform->>Realtime: Broadcast question to audience
  Realtime-->>UI: Push question data

  Platform-->>UI: Host UI updated
```

### Data Elements

**Request**:
```json
{
  "session_id": "sess_xyz",
  "action": "next_question"
}
```

**Response**:
```json
{
  "session_id": "sess_xyz",
  "current_question": {
    "question_id": "q_456",
    "text": "What is 2+2?",
    "options": [
      {"id": "opt_1", "text": "3"},
      {"id": "opt_2", "text": "4"},
      {"id": "opt_3", "text": "5"},
      {"id": "opt_4", "text": "6"}
    ],
    "state": "OPEN"
  }
}
```

**Realtime Broadcast (to Audience)**:
```json
{
  "type": "question_opened",
  "session_id": "sess_xyz",
  "question": {
    "question_id": "q_456",
    "text": "What is 2+2?",
    "options": [
      {"id": "opt_1", "text": "3"},
      {"id": "opt_2", "text": "4"},
      {"id": "opt_3", "text": "5"},
      {"id": "opt_4", "text": "6"}
    ]
  }
}
```

---

## Flow 4: View Results (Host & Audience)

### Description
After a question is closed, results are aggregated and displayed.

### Sequence

```mermaid
sequenceDiagram
  autonumber
  actor Host
  participant UI as Host UI
  participant Platform as Platform Kernel
  participant Quiz as Quiz Feature
  participant DB as Database
  participant Realtime as Realtime Hub
  participant AudienceUI as Audience UI

  Host->>UI: Click "Close Question"
  UI->>Platform: Close question request

  Platform->>Quiz: Close question
  Quiz->>Quiz: Set question state = CLOSED
  Quiz->>DB: Aggregate answers
  DB-->>Quiz: Answer counts per option

  Quiz-->>Platform: Results ready
  Platform->>Realtime: Broadcast results
  Realtime-->>UI: Push results to host
  Realtime-->>AudienceUI: Push results to audience

  UI-->>Host: Display bar chart with counts
  AudienceUI-->>Host: Display correct answer + results
```

### Data Elements

**Results Payload**:
```json
{
  "type": "question_results",
  "session_id": "sess_xyz",
  "question_id": "q_456",
  "correct_option": "opt_2",
  "results": [
    {"option_id": "opt_1", "count": 12, "percentage": 15},
    {"option_id": "opt_2", "count": 60, "percentage": 75},
    {"option_id": "opt_3", "count": 6, "percentage": 7.5},
    {"option_id": "opt_4", "count": 2, "percentage": 2.5}
  ],
  "total_responses": 80
}
```

---

## Summary

These data flows demonstrate:
- Clear separation between Services, Platform, and Features
- Realtime broadcasting for live updates
- Answer validation and aggregation in Quiz Feature
- Host control over quiz progression

---

## Flow 5: Create and Edit Quiz (Host - Quiz Builder)

### Description
A host creates a new quiz, adds questions, and saves changes with autosave.

### Actors
- Host
- Frontend UI
- API Service (Quiz endpoints)
- Database
- Quiz Feature

### Sequence

```mermaid
sequenceDiagram
  autonumber
  actor Host
  participant UI as Quiz Builder UI
  participant API as API Service
  participant Quiz as Quiz Feature
  participant DB as Database

  Host->>UI: Click "Create New Quiz"
  UI->>API: POST /quizzes {title: "Science Quiz"}

  API->>Quiz: Create quiz command
  Quiz->>DB: INSERT quiz (status: DRAFT)
  DB-->>Quiz: quiz_id
  Quiz-->>API: Quiz created response
  API-->>UI: quiz_id + empty quiz

  Host->>UI: Enter question text
  UI-->>UI: 1-second debounce timer starts

  Host->>UI: Enter first option
  UI-->>UI: Timer resets (typing continues)

  Host->>UI: Stop typing (1 second elapses)
  UI-->>UI: Show "Saving..." indicator
  UI->>API: PATCH /quizzes/{quiz_id}/questions/{q_id} {text: "What is 2+2?", options: [...], correct_option_index: 1}

  API->>Quiz: Update question command
  Quiz->>DB: UPDATE question
  DB-->>Quiz: OK
  Quiz-->>API: Question updated
  API-->>UI: Success response

  UI-->>UI: Show "Saved" checkmark for 2s
  Host-->>UI: Saved confirmation

  Host->>UI: Click "Add Question" button
  UI->>API: POST /quizzes/{quiz_id}/questions {}
  API->>Quiz: Create question command
  Quiz->>DB: INSERT question (order: auto-increment)
  DB-->>Quiz: question_id
  Quiz-->>API: Question created
  API-->>UI: New question_id

  Host->>UI: Drag question to new position
  UI->>API: POST /quizzes/{quiz_id}/reorder {question_orders: [...]}
  API->>Quiz: Reorder questions command
  Quiz->>DB: UPDATE question orders
  DB-->>Quiz: OK
  Quiz-->>API: Questions reordered
  API-->>UI: Success

  Host->>UI: Click "Publish Quiz"
  UI->>API: POST /quizzes/{quiz_id}/validate
  API->>Quiz: Validate quiz command
  Quiz-->>API: Validation result {valid: true, errors: []}
  API-->>UI: Validation OK

  UI->>API: POST /quizzes/{quiz_id}/publish
  API->>Quiz: Publish quiz command
  Quiz->>DB: UPDATE quiz (status: READY)
  DB-->>Quiz: OK
  Quiz-->>API: Quiz published
  API-->>UI: Redirect to /dashboard
```

### JSON Payloads

**Create Quiz**:
```json
POST /quizzes
{
  "title": "Weekly Science Quiz",
  "description": "Test your knowledge"
}

Response (201 Created):
{
  "quiz_id": "qz_789",
  "title": "Weekly Science Quiz",
  "status": "DRAFT",
  "created_at": "2026-01-27T10:00:00Z"
}
```

**Add Question**:
```json
POST /quizzes/{quiz_id}/questions
{
  "text": "What is 2+2?",
  "options": [
    {"text": "3", "order": 1},
    {"text": "4", "order": 2},
    {"text": "5", "order": 3},
    {"text": "6", "order": 4}
  ],
  "correct_option_index": 1
}

Response (201 Created):
{
  "question_id": "q_456",
  "order": 1,
  "text": "What is 2+2?",
  "options": [
    {"option_id": "opt_1", "text": "3", "order": 1},
    {"option_id": "opt_2", "text": "4", "order": 2},
    {"option_id": "opt_3", "text": "5", "order": 3},
    {"option_id": "opt_4", "text": "6", "order": 4}
  ],
  "correct_option_id": "opt_2"
}
```

**Validate Quiz**:
```json
POST /quizzes/{quiz_id}/validate

Response (200 OK):
{
  "valid": true,
  "errors": []
}

OR (Invalid):
{
  "valid": false,
  "errors": [
    "Quiz must have at least 1 question",
    "Question 1: missing correct answer"
  ]
}
```

**Publish Quiz**:
```json
POST /quizzes/{quiz_id}/publish

Response (200 OK):
{
  "quiz_id": "qz_789",
  "status": "READY",
  "published_at": "2026-01-27T10:20:00Z"
}
```

---

## Updated Summary

These data flows demonstrate:
- Clear separation between Services, Platform, and Features
- Quiz builder autosave with 1-second debounce
- Validation before publishing
- Batch API calls for PATCH operations
- Realtime broadcasting for live updates
- Answer validation and aggregation in Quiz Feature
- Host control over quiz progression
