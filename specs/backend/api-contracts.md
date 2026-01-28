# API Contracts (MVP)

This document defines all API endpoints, request/response schemas, and error codes for the Swaya.me MVP.

---

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://swaya.me`

---

## API Versioning

- **Current Version**: v1
- **Prefix**: `/api/v1`

All endpoints below are prefixed with `/api/v1`.

---

## Authentication Endpoints

### POST /auth/login

Authenticate host and receive JWT token.

**Request**:
```json
{
  "email": "host@example.com",
  "password": "SecurePass123"
}
```

**Response (200 OK)**:
```json
{
  "access_token": "EXAMPLE_JWT_TOKEN",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "usr_123",
    "email": "host@example.com",
    "full_name": "John Doe"
  }
}
```

**Errors**:
- `401 INVALID_CREDENTIALS`: Invalid email or password
- `429 RATE_LIMIT_EXCEEDED`: Too many login attempts

---

## Quiz Management Endpoints

### POST /quizzes

Create a new quiz (host only).

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Request**:
```json
{
  "title": "Weekly Science Quiz",
  "description": "Test your science knowledge"
}
```

**Response (201 Created)**:
```json
{
  "quiz_id": "qz_789",
  "title": "Weekly Science Quiz",
  "description": "Test your science knowledge",
  "host_id": "usr_123",
  "status": "DRAFT",
  "created_at": "2026-01-27T10:00:00Z"
}
```

**Errors**:
- `401 UNAUTHORIZED`: Missing or invalid JWT
- `400 BAD_REQUEST`: Invalid request payload

---

### GET /quizzes

List all quizzes created by authenticated host.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK)**:
```json
{
  "quizzes": [
    {
      "quiz_id": "qz_789",
      "title": "Weekly Science Quiz",
      "status": "READY",
      "question_count": 5,
      "created_at": "2026-01-27T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

### GET /quizzes/{quiz_id}

Get quiz details including questions.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK)**:
```json
{
  "quiz_id": "qz_789",
  "title": "Weekly Science Quiz",
  "description": "Test your science knowledge",
  "status": "READY",
  "host_id": "usr_123",
  "questions": [
    {
      "question_id": "q_456",
      "text": "What is 2+2?",
      "order": 1,
      "options": [
        {"option_id": "opt_1", "text": "3", "order": 1},
        {"option_id": "opt_2", "text": "4", "order": 2},
        {"option_id": "opt_3", "text": "5", "order": 3},
        {"option_id": "opt_4", "text": "6", "order": 4}
      ],
      "correct_option_id": "opt_2"
    }
  ],
  "created_at": "2026-01-27T10:00:00Z"
}
```

**Errors**:
- `404 NOT_FOUND`: Quiz not found
- `403 FORBIDDEN`: Quiz belongs to another host

---

### POST /quizzes/{quiz_id}/questions

Add a question to a quiz.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Request**:
```json
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
```

**Response (201 Created)**:
```json
{
  "question_id": "q_456",
  "quiz_id": "qz_789",
  "text": "What is 2+2?",
  "order": 1,
  "options": [
    {"option_id": "opt_1", "text": "3", "order": 1},
    {"option_id": "opt_2", "text": "4", "order": 2},
    {"option_id": "opt_3", "text": "5", "order": 3},
    {"option_id": "opt_4", "text": "6", "order": 4}
  ],
  "correct_option_id": "opt_2"
}
```

**Validation Rules**:
- Question text: required, 1-500 characters
- Options: exactly 4 required
- Option text: required, 1-200 characters each
- Correct option index: 0-3 (zero-indexed)

**Errors**:
- `400 BAD_REQUEST`: Invalid payload or validation failure
- `404 NOT_FOUND`: Quiz not found
- `403 FORBIDDEN`: Quiz belongs to another host

---

### PATCH /quizzes/{quiz_id}

Update quiz metadata (title, description).

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Request**:
```json
{
  "title": "Updated Science Quiz",
  "description": "Updated description"
}
```

**Response (200 OK)**:
```json
{
  "quiz_id": "qz_789",
  "title": "Updated Science Quiz",
  "description": "Updated description",
  "status": "DRAFT",
  "updated_at": "2026-01-27T10:15:00Z"
}
```

**Errors**:
- `404 NOT_FOUND`: Quiz not found
- `403 FORBIDDEN`: Quiz belongs to another host

---

### PATCH /quizzes/{quiz_id}/questions/{question_id}

Update question text or correct answer.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Request**:
```json
{
  "text": "What is 2+3?",
  "options": [
    {"text": "3", "order": 1},
    {"text": "4", "order": 2},
    {"text": "5", "order": 3},
    {"text": "6", "order": 4}
  ],
  "correct_option_index": 2
}
```

**Response (200 OK)**:
```json
{
  "question_id": "q_456",
  "quiz_id": "qz_789",
  "text": "What is 2+3?",
  "order": 1,
  "options": [
    {"option_id": "opt_1", "text": "3", "order": 1},
    {"option_id": "opt_2", "text": "4", "order": 2},
    {"option_id": "opt_3", "text": "5", "order": 3},
    {"option_id": "opt_4", "text": "6", "order": 4}
  ],
  "correct_option_id": "opt_3",
  "updated_at": "2026-01-27T10:15:00Z"
}
```

**Errors**:
- `404 NOT_FOUND`: Question not found
- `403 FORBIDDEN`: Question belongs to another host's quiz

---

### DELETE /quizzes/{quiz_id}/questions/{question_id}

Delete a question from a quiz.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (204 No Content)**:
```
(empty response)
```

**Errors**:
- `404 NOT_FOUND`: Question not found
- `403 FORBIDDEN`: Question belongs to another host's quiz

---

### POST /quizzes/{quiz_id}/reorder

Reorder questions in a quiz.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Request**:
```json
{
  "question_orders": [
    {"question_id": "q_789", "order": 1},
    {"question_id": "q_456", "order": 2},
    {"question_id": "q_123", "order": 3}
  ]
}
```

**Response (200 OK)**:
```json
{
  "quiz_id": "qz_789",
  "questions": [
    {"question_id": "q_789", "order": 1},
    {"question_id": "q_456", "order": 2},
    {"question_id": "q_123", "order": 3}
  ]
}
```

---

### POST /quizzes/{quiz_id}/validate

Validate quiz completeness before publishing.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK - Valid)**:
```json
{
  "valid": true,
  "errors": []
}
```

**Response (200 OK - Invalid)**:
```json
{
  "valid": false,
  "errors": [
    "Quiz title is required",
    "Quiz must have at least 1 question",
    "Question 1 is missing correct answer",
    "Question 2 must have exactly 4 options"
  ]
}
```

---

### POST /quizzes/{quiz_id}/publish

Publish quiz (transition from DRAFT to READY).

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Request**:
```json
{}
```

**Response (200 OK)**:
```json
{
  "quiz_id": "qz_789",
  "status": "READY",
  "published_at": "2026-01-27T10:20:00Z"
}
```

**Errors**:
- `400 BAD_REQUEST`: Quiz validation failed (missing required fields)
- `409 CONFLICT`: Quiz already published or already in use

---

### DELETE /quizzes/{quiz_id}

Delete a quiz (host only).

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (204 No Content)**:
```
(empty response)
```

**Errors**:
- `404 NOT_FOUND`: Quiz not found
- `403 FORBIDDEN`: Quiz belongs to another host
- `409 CONFLICT`: Cannot delete quiz in use (active session)

---

## Session Management Endpoints

### POST /quizzes/{quiz_id}/sessions

Start a live quiz session (host only).

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (201 Created)**:
```json
{
  "session_id": "sess_xyz",
  "quiz_id": "qz_789",
  "join_code": "ABC123",
  "status": "CREATED",
  "started_at": null,
  "created_at": "2026-01-27T11:00:00Z"
}
```

**Errors**:
- `400 BAD_REQUEST`: Quiz not ready (no questions)
- `409 CONFLICT`: Active session already exists for this quiz

---

### POST /sessions/{session_id}/start

Start the quiz session and open first question.

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK)**:
```json
{
  "session_id": "sess_xyz",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_456",
    "text": "What is 2+2?",
    "options": [
      {"option_id": "opt_1", "text": "3"},
      {"option_id": "opt_2", "text": "4"},
      {"option_id": "opt_3", "text": "5"},
      {"option_id": "opt_4", "text": "6"}
    ]
  },
  "started_at": "2026-01-27T11:05:00Z"
}
```

---

### POST /sessions/{session_id}/advance

Move to next question (host only).

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK)**:
```json
{
  "session_id": "sess_xyz",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_457",
    "text": "What is the capital of France?",
    "options": [
      {"option_id": "opt_5", "text": "London"},
      {"option_id": "opt_6", "text": "Paris"},
      {"option_id": "opt_7", "text": "Berlin"},
      {"option_id": "opt_8", "text": "Madrid"}
    ]
  }
}
```

**Errors**:
- `404 NOT_FOUND`: Session not found
- `400 BAD_REQUEST`: No more questions

---

### POST /sessions/{session_id}/end

End the quiz session (host only).

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK)**:
```json
{
  "session_id": "sess_xyz",
  "status": "ENDED",
  "ended_at": "2026-01-27T11:30:00Z"
}
```

---

## Audience Endpoints

### POST /sessions/join

Join a quiz session using join code (audience).

**Request**:
```json
{
  "join_code": "ABC123"
}
```

**Response (200 OK)**:
```json
{
  "session_id": "sess_xyz",
  "participant_id": "part_123",
  "quiz_title": "Weekly Science Quiz",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_456",
    "text": "What is 2+2?",
    "options": [
      {"option_id": "opt_1", "text": "3"},
      {"option_id": "opt_2", "text": "4"},
      {"option_id": "opt_3", "text": "5"},
      {"option_id": "opt_4", "text": "6"}
    ]
  }
}
```

**Errors**:
- `404 SESSION_NOT_FOUND`: Invalid join code or session ended
- `429 RATE_LIMIT_EXCEEDED`: Too many join attempts

---

### POST /sessions/{session_id}/submit

Submit answer to current question (audience).

**Request**:
```json
{
  "participant_id": "part_123",
  "question_id": "q_456",
  "option_id": "opt_2"
}
```

**Response (200 OK)**:
```json
{
  "submission_id": "sub_999",
  "status": "recorded",
  "question_id": "q_456",
  "selected_option": "opt_2",
  "submitted_at": "2026-01-27T11:10:00Z"
}
```

**Errors**:
- `400 SUBMISSION_REJECTED`: Question closed, duplicate submission, or invalid state
- `404 NOT_FOUND`: Session, participant, or question not found

---

### GET /sessions/{session_id}/results/{question_id}

Get results for a closed question (host and audience).

**Response (200 OK)**:
```json
{
  "question_id": "q_456",
  "text": "What is 2+2?",
  "correct_option_id": "opt_2",
  "results": [
    {"option_id": "opt_1", "text": "3", "count": 5, "percentage": 10.0},
    {"option_id": "opt_2", "text": "4", "count": 40, "percentage": 80.0},
    {"option_id": "opt_3", "text": "5", "count": 3, "percentage": 6.0},
    {"option_id": "opt_4", "text": "6", "count": 2, "percentage": 4.0}
  ],
  "total_responses": 50
}
```

**Errors**:
- `400 BAD_REQUEST`: Question not yet closed

---

## Error Response Format

All errors follow this format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "validation_error_if_applicable"
  }
}
```

---

## HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request payload or validation error |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict (e.g., duplicate session) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |

---

## Realtime Updates (WebSocket or Polling)

**To be finalized**: MVP may use polling or WebSocket based on implementation complexity.

### Polling Approach (Simpler)
- Audience polls `/sessions/{session_id}/status` every 2 seconds
- Returns current question or results update

### WebSocket Approach (More Realtime)
- Connect to `ws://host/sessions/{session_id}/live`
- Server pushes question_opened, question_closed, results_updated events

**Decision pending**: Will be documented in realtime.md
