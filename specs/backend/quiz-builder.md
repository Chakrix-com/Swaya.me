# Quiz Builder Feature (Internal Design)

This document defines the **internal design** of the Quiz Builder feature for the MVP.
It focuses on the quiz authoring workflow, validation rules, and state management.

---

## Feature Overview

The Quiz Builder enables hosts to create and edit quizzes before going live.

**Scope**:
- Create new quiz (DRAFT status)
- Edit quiz metadata (title, description)
- Add/edit/delete questions (MCQ only, 4 options each)
- Mark correct answer for each question
- Reorder questions
- Validate quiz completeness
- Preview quiz
- Publish quiz (transition to READY)

**Non-Scope**:
- Co-editing/collaboration (single host per quiz)
- Media uploads (images/video)
- Quiz settings (shuffle, timer, leaderboard)
- Templates or cloning

---

## Quiz States (Builder Perspective)

| State | Description | Allowed Actions | Constraints |
|------|-------------|-----------------|------------|
| DRAFT | Quiz is being created or edited | Edit metadata, add/edit questions, save, preview, publish, delete | Not visible to audience, cannot be used in session |
| READY | Quiz is published and ready for live session | Start session, duplicate (post-MVP), archive (post-MVP) | Immutable during active session, can be modified between sessions |
| ARCHIVED | Quiz is no longer active (post-MVP) | View, restore (post-MVP) | Read-only, cannot be modified |

---

## Quiz Builder Workflow (MVP)

### Phase 1: Create Draft

**User Action**: Host clicks "Create New Quiz"

| Step | Action | API Call | Validation | State Change |
|------|--------|----------|------------|--------------|
| 1 | Click "Create" | POST /quizzes | Requires title | Quiz created in DRAFT |
| 2 | Enter title | PATCH /quizzes/{quiz_id} | 1-255 characters | Metadata updated |
| 3 | Enter description | PATCH /quizzes/{quiz_id} | 0-1000 characters (optional) | Metadata updated |

**Example Flow**:
```
Host → [Create Quiz] → POST /quizzes
  ↓ (empty DRAFT created)
Host → [Enter title] → PATCH /quizzes/{quiz_id}
  ↓ (metadata updated)
Host → [Dashboard view updated]
```

### Phase 2: Add Questions

**User Action**: Host clicks "Add Question"

| Step | Action | API Call | Validation | Result |
|------|--------|----------|------------|--------|
| 1 | Click "Add Question" | POST /quizzes/{quiz_id}/questions | No validation required | Question card appears (order auto-incremented) |
| 2 | Enter question text | PATCH /quizzes/{quiz_id}/questions/{q_id} | 1-500 characters | Question updated |
| 3 | Enter option 1-4 | PATCH /quizzes/{quiz_id}/questions/{q_id} | 1-200 chars per option | Options updated |
| 4 | Select correct option | PATCH /quizzes/{quiz_id}/questions/{q_id} | Must select one | Correct answer marked |

**Validation Rules**:
- Question text: required, 1-500 characters
- Options: exactly 4 required
- Option text: required, 1-200 characters each
- Exactly one option marked correct

### Phase 3: Edit & Reorder

**User Actions**:
- Edit question text/options → PATCH endpoint
- Delete question → DELETE endpoint
- Reorder questions → POST /reorder endpoint

**Reorder Mechanism**:
```json
POST /quizzes/{quiz_id}/reorder
{
  "question_orders": [
    {"question_id": "q_789", "order": 1},
    {"question_id": "q_456", "order": 2},
    {"question_id": "q_123", "order": 3}
  ]
}
```

### Phase 4: Validate & Preview

**User Actions**:
- Click "Preview" → Read-only view of quiz as audience sees it
- Click "Validate" → Check for missing fields

**Validation Rules**:
1. Quiz has a title
2. Quiz has at least 1 question
3. Each question has exactly 4 options
4. Each question has one marked correct answer
5. All question text is non-empty

**Validation Response**:
```json
{
  "valid": true,
  "errors": []
}
```

Or with errors:
```json
{
  "valid": false,
  "errors": [
    "Quiz title is required",
    "Question 1: text cannot be empty",
    "Question 2: must have exactly 4 options",
    "Question 3: must mark one correct answer"
  ]
}
```

### Phase 5: Publish

**User Action**: Host clicks "Publish" or "Ready"

| Step | Action | API Call | Validation | State Change |
|------|--------|----------|------------|--------------|
| 1 | Click "Publish" | POST /quizzes/{quiz_id}/validate | Full validation | Validation performed |
| 2 | If valid | POST /quizzes/{quiz_id}/publish | Status check | Status → READY |
| 3 | If invalid | Show errors | Error display | Redirect to fix |

**Publishing Rules**:
- Quiz must pass all validation checks
- Can only transition from DRAFT to READY
- Once READY, quiz becomes available in "Start Session" dropdown

---

## Autosave Strategy (MVP)

**Goal**: Minimize data loss without overwhelming the server.

**Implementation**:
- Client-side debounce: 1 second wait after last keystroke
- Batch updates: Collect all changes in one PATCH
- Visual feedback: "Saving..." → "Saved" indicator

**Example (Edit Question)**:
```
Host types "What is..." → Timer starts (1s)
  ↓ (no API call yet)
Host continues typing "...the capital of France?" → Timer resets
  ↓ (wait 1s with no changes)
1 second elapses → PATCH /quizzes/{q_id}
  ↓
"Saved" indicator shown
```

**Autosave Payload**:
```json
PATCH /quizzes/{quiz_id}/questions/{question_id}
{
  "text": "What is the capital of France?",
  "options": [
    {"text": "Paris", "order": 1},
    {"text": "Lyon", "order": 2},
    {"text": "Marseille", "order": 3},
    {"text": "Nice", "order": 4}
  ],
  "correct_option_index": 0
}
```

---

## Data Consistency Rules

### During Editing
- PATCH endpoints are idempotent (same payload = same result)
- No partial updates (always send complete question)
- Optimistic UI updates (immediate local display)

### During Session
- Quiz cannot be modified if active session exists (409 CONFLICT)
- Read-only access to quiz after READY transition

### Deletion Safety
- Question deletion updates order of subsequent questions
- Quiz deletion only allowed if no active sessions referencing it

---

## Error Handling

| Error | Condition | Response | Recovery |
|-------|-----------|----------|----------|
| Quiz not found | DELETE/PATCH quiz that doesn't exist | 404 NOT_FOUND | Redirect to dashboard |
| Unauthorized | Host doesn't own quiz | 403 FORBIDDEN | Redirect to dashboard |
| Validation failed | Quiz missing required fields | 400 BAD_REQUEST | Show error list, highlight missing fields |
| Conflict | Attempt to delete quiz in use | 409 CONFLICT | Show "Cannot delete active quiz" message |
| Rate limited | Too many rapid saves | 429 RATE_LIMIT | Show backoff message, retry after X seconds |

---

## Database Constraints

**Quiz Immutability During Session**:
```sql
-- Prevent modification of quiz during active session
ALTER TABLE quizzes ADD CONSTRAINT check_status_immutable
  CHECK (status = 'DRAFT' OR session_id IS NULL);
```

**Question Integrity**:
```sql
-- Enforce 4 options per question
ALTER TABLE questions ADD CONSTRAINT check_option_count
  CHECK (option_count = 4);

-- Enforce one correct answer per question
ALTER TABLE questions ADD CONSTRAINT check_correct_answer
  CHECK (correct_option_id IS NOT NULL);
```

---

## Testability

### Unit Tests (Quiz Builder Feature)
- Quiz creation and validation
- Question CRUD operations
- Reordering logic
- Publish transition
- Validation rule enforcement
- Autosave mechanism (client-side)

### Integration Tests (API Layer)
- PATCH /quizzes endpoint with idempotency
- DELETE quiz authorization checks
- Validation endpoint with various error states
- Conflict detection (quiz in use)

### Acceptance Tests
- Create → Edit → Preview → Publish flow
- Validation error messages display correctly
- Unsaved changes warning before navigation
- Autosave feedback indicators

---

## Performance Considerations

| Concern | Target | Strategy |
|---------|--------|----------|
| Quiz load time | < 500ms | Index quiz_id + host_id, eager load questions |
| Save latency | < 1s | Async batch updates, client-side debounce |
| Reorder operation | < 500ms | Single transaction, order index |
| Validation check | < 200ms | In-memory calculation, no DB query |

---

## Future Enhancements (Post-MVP)

- Question templates library
- Bulk import from CSV
- Question banks and reusable questions
- Collaborative editing (co-hosts)
- Quiz versioning and history
- Media upload support (images/video)
- Question settings (individual timers, scoring)
- AI-assisted question generation

---

## References

- [mvp-scope.md](../overview/mvp-scope.md) — MVP scope definition
- [domain-model.md](./domain-model.md) — Core domain entities
- [api-contracts.md](./api-contracts.md) — Complete API specification
- [persistence.md](./persistence.md) — Database schema

