# Swaya.me API Reference

## Base URL
- Development: `http://localhost:8000`
- Production: `https://swaya.me`

All endpoints are prefixed with `/api/v1`

---

## Authentication

### Register User
```
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe",
  "tenant_name": "My Organization"
}

Response 201:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "tenant_id": 1,
    "tier": "free"
  }
}
```

### Login
```
POST /api/v1/auth/login

{
  "email": "user@example.com",
  "password": "SecurePass123"
}

Response 200: (same as register)
```

### Get Current User
```
GET /api/v1/auth/me
Authorization: Bearer {token}

Response 200:
{
  "user": { ... }
}
```

---

## Quiz Management (Host - Requires Auth)

### Create Quiz
```
POST /api/v1/quizzes
Authorization: Bearer {token}

{
  "title": "JavaScript Basics",
  "description": "Test your JS knowledge",
  "event_id": 1
}

Response 201:
{
  "id": 1,
  "title": "JavaScript Basics",
  "status": "draft",
  "question_count": 0,
  ...
}
```

### List Quizzes
```
GET /api/v1/quizzes?event_id=1
Authorization: Bearer {token}

Response 200:
[
  {
    "id": 1,
    "title": "JavaScript Basics",
    "status": "draft",
    "question_count": 5
  }
]
```

### Get Quiz
```
GET /api/v1/quizzes/{id}
Authorization: Bearer {token}

Response 200:
{
  "id": 1,
  "title": "...",
  "questions": [
    {
      "id": 1,
      "text": "What is a closure?",
      "options": ["A", "B", "C", "D"],
      "order": 0,
      "correct_answer_index": 2
    }
  ]
}
```

### Update Quiz
```
PUT /api/v1/quizzes/{id}
Authorization: Bearer {token}

{
  "title": "Updated Title",
  "description": "New description"
}
```

### Publish Quiz
```
POST /api/v1/quizzes/{id}/publish
Authorization: Bearer {token}

Response 200: (quiz with status="ready")
```

### Delete Quiz
```
DELETE /api/v1/quizzes/{id}
Authorization: Bearer {token}

Response 204: No Content
```

---

## Question Management (Host - Requires Auth)

### Add Question
```
POST /api/v1/quizzes/{quiz_id}/questions
Authorization: Bearer {token}

{
  "text": "What is 2 + 2?",
  "options": ["3", "4", "5", "6"],
  "correct_answer_index": 1
}

Response 201:
{
  "id": 1,
  "text": "What is 2 + 2?",
  "options": ["3", "4", "5", "6"],
  "order": 0
}
```

### Update Question
```
PUT /api/v1/quizzes/questions/{id}
Authorization: Bearer {token}

{
  "text": "Updated question text",
  "options": ["A", "B", "C", "D"],
  "correct_answer_index": 0
}
```

### Delete Question
```
DELETE /api/v1/quizzes/questions/{id}
Authorization: Bearer {token}

Response 204: No Content
```

---

## Session Management

### Start Session (Host)
```
POST /api/v1/quizzes/sessions/start?quiz_id=1
Authorization: Bearer {token}

Response 201:
{
  "id": 1,
  "quiz_id": 1,
  "quiz_title": "JavaScript Basics",
  "status": "created",
  "current_question_index": -1,
  "join_code": "ABC123",
  "participant_count": 0
}
```

### Join Session (Audience - No Auth)
```
POST /api/v1/quizzes/sessions/join

{
  "join_code": "ABC123",
  "display_name": "John"
}

Response 200:
{
  "session_id": 1,
  "session_token": "token_abc123...",
  "participant_id": 1,
  "quiz_title": "JavaScript Basics",
  "status": "created"
}
```

### Advance Question (Host)
```
POST /api/v1/quizzes/sessions/{id}/advance
Authorization: Bearer {token}

Response 200:
{
  "id": 1,
  "status": "active",
  "current_question_index": 0,
  "current_question_status": "open",
  ...
}
```

### End Session (Host)
```
POST /api/v1/quizzes/sessions/{id}/end
Authorization: Bearer {token}

Response 200:
{
  "status": "ended",
  ...
}
```

---

## Answer Submission (Audience)

### Submit Answer
```
POST /api/v1/quizzes/sessions/submit-answer?session_token={token}

{
  "question_id": 1,
  "selected_option_index": 2
}

Response 200:
{
  "success": true,
  "message": "Answer submitted successfully",
  "is_correct": null  // Revealed after question closes
}
```

### Get Results
```
GET /api/v1/quizzes/sessions/{id}/results?session_token={token}

Response 200:
{
  "session_id": 1,
  "quiz_title": "JavaScript Basics",
  "total_questions": 10,
  "participant_score": 10,
  "participant_correct": 8,
  "question_results": [
    {
      "question_id": 1,
      "question_text": "...",
      "correct_answer_index": 2,
      "answer_distribution": [5, 10, 25, 8],
      "total_answers": 48,
      "participant_answer": 2
    }
  ]
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Quiz must have at least one question"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid token or expired"
}
```

### 404 Not Found
```json
{
  "detail": "Quiz not found"
}
```

### 429 Too Many Requests
```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests",
  "retry_after": 60
}
```

---

## Rate Limits

| Endpoint | Limit | Scope |
|----------|-------|-------|
| POST /auth/login | 5/minute | IP |
| POST /sessions/join | 10/minute | IP |
| POST /submit-answer | 100/minute | Participant |
| POST /quizzes | 20/hour | User |
| GET * | 1000/minute | IP |

---

## Tier Limits

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Participants per session | 50 | 1,000 | 10,000 |
| Questions per quiz | 10 | 100 | 1,000 |
| Concurrent events | 1 | 5 | 50 |

---

## WebSocket Events (Coming Soon)

```
ws://localhost:8000/ws/session/{session_id}

Events:
- question_opened
- answer_submitted
- question_closed
- session_ended
```
