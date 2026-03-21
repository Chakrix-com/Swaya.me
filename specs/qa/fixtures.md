# Test Fixtures & Sample Data

This document provides sample payloads, fixtures, and test data for development and testing.

---

## Authentication Fixtures

### Login Request (Valid)
```json
{
  "email": "host@example.com",
  "password": "password123"
}
```

### Login Response (Success)
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

### Login Response (Error)
```json
{
  "error": "INVALID_CREDENTIALS",
  "message": "Invalid email or password"
}
```

---

## Quiz Management Fixtures

### Create Quiz Request
```json
{
  "title": "Weekly Science Quiz",
  "description": "Test your science knowledge"
}
```

### Create Quiz Response
```json
{
  "quiz_id": "qz_789abc",
  "title": "Weekly Science Quiz",
  "description": "Test your science knowledge",
  "host_id": "usr_123",
  "status": "DRAFT",
  "created_at": "2026-01-27T10:00:00Z",
  "updated_at": "2026-01-27T10:00:00Z"
}
```

### Get Quiz Response (With Questions)
```json
{
  "quiz_id": "qz_789abc",
  "title": "Weekly Science Quiz",
  "description": "Test your science knowledge",
  "status": "READY",
  "host_id": "usr_123",
  "questions": [
    {
      "question_id": "q_456def",
      "text": "What is 2+2?",
      "order": 1,
      "options": [
        {
          "option_id": "opt_1",
          "text": "3",
          "order": 1
        },
        {
          "option_id": "opt_2",
          "text": "4",
          "order": 2
        },
        {
          "option_id": "opt_3",
          "text": "5",
          "order": 3
        },
        {
          "option_id": "opt_4",
          "text": "6",
          "order": 4
        }
      ],
      "correct_option_id": "opt_2"
    },
    {
      "question_id": "q_457ghi",
      "text": "What is the capital of France?",
      "order": 2,
      "options": [
        {
          "option_id": "opt_5",
          "text": "London",
          "order": 1
        },
        {
          "option_id": "opt_6",
          "text": "Paris",
          "order": 2
        },
        {
          "option_id": "opt_7",
          "text": "Berlin",
          "order": 3
        },
        {
          "option_id": "opt_8",
          "text": "Madrid",
          "order": 4
        }
      ],
      "correct_option_id": "opt_6"
    }
  ],
  "created_at": "2026-01-27T10:00:00Z",
  "updated_at": "2026-01-27T10:05:00Z"
}
```

### Add Question Request
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

### Add Question Response
```json
{
  "question_id": "q_456def",
  "quiz_id": "qz_789abc",
  "text": "What is 2+2?",
  "order": 1,
  "options": [
    {"option_id": "opt_1", "text": "3", "order": 1},
    {"option_id": "opt_2", "text": "4", "order": 2},
    {"option_id": "opt_3", "text": "5", "order": 3},
    {"option_id": "opt_4", "text": "6", "order": 4}
  ],
  "correct_option_id": "opt_2",
  "created_at": "2026-01-27T10:02:00Z"
}
```

---

## Session Management Fixtures

### Start Session Response
```json
{
  "session_id": "sess_xyz123",
  "quiz_id": "qz_789abc",
  "join_code": "ABC123",
  "status": "CREATED",
  "started_at": null,
  "created_at": "2026-01-27T11:00:00Z"
}
```

### Start Quiz Response
```json
{
  "session_id": "sess_xyz123",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_456def",
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

### Advance Question Response
```json
{
  "session_id": "sess_xyz123",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_457ghi",
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

### End Session Response
```json
{
  "session_id": "sess_xyz123",
  "status": "ENDED",
  "ended_at": "2026-01-27T11:30:00Z"
}
```

---

## Audience Participation Fixtures

### Join Session Request
```json
{
  "join_code": "ABC123"
}
```

### Join Session Response (Success)
```json
{
  "session_id": "sess_xyz123",
  "participant_id": "part_456abc",
  "quiz_title": "Weekly Science Quiz",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_456def",
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

### Join Session Response (Error)
```json
{
  "error": "SESSION_NOT_FOUND",
  "message": "Quiz session not found or has ended"
}
```

### Submit Answer Request
```json
{
  "participant_id": "part_456abc",
  "question_id": "q_456def",
  "option_id": "opt_2"
}
```

### Submit Answer Response (Success)
```json
{
  "submission_id": "sub_999xyz",
  "status": "recorded",
  "question_id": "q_456def",
  "selected_option": "opt_2",
  "submitted_at": "2026-01-27T11:10:00Z"
}
```

### Submit Answer Response (Error - Duplicate)
```json
{
  "error": "SUBMISSION_REJECTED",
  "reason": "DUPLICATE_SUBMISSION",
  "message": "You have already answered this question"
}
```

### Submit Answer Response (Error - Question Closed)
```json
{
  "error": "SUBMISSION_REJECTED",
  "reason": "QUESTION_CLOSED",
  "message": "Question is no longer accepting answers"
}
```

---

## Results Fixtures

### Get Results Response
```json
{
  "question_id": "q_456def",
  "text": "What is 2+2?",
  "correct_option_id": "opt_2",
  "results": [
    {
      "option_id": "opt_1",
      "text": "3",
      "count": 5,
      "percentage": 10.0
    },
    {
      "option_id": "opt_2",
      "text": "4",
      "count": 40,
      "percentage": 80.0
    },
    {
      "option_id": "opt_3",
      "text": "5",
      "count": 3,
      "percentage": 6.0
    },
    {
      "option_id": "opt_4",
      "text": "6",
      "count": 2,
      "percentage": 4.0
    }
  ],
  "total_responses": 50
}
```

### Poll Session Status Response (Question Open)
```json
{
  "session_id": "sess_xyz123",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_456def",
    "text": "What is 2+2?",
    "options": [
      {"option_id": "opt_1", "text": "3"},
      {"option_id": "opt_2", "text": "4"},
      {"option_id": "opt_3", "text": "5"},
      {"option_id": "opt_4", "text": "6"}
    ],
    "state": "OPEN"
  },
  "live_results": null,
  "last_updated": "2026-01-27T11:10:00Z"
}
```

### Poll Session Status Response (Question Closed)
```json
{
  "session_id": "sess_xyz123",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_456def",
    "text": "What is 2+2?",
    "state": "CLOSED"
  },
  "live_results": {
    "correct_option_id": "opt_2",
    "results": [
      {"option_id": "opt_1", "count": 5, "percentage": 10.0},
      {"option_id": "opt_2", "count": 40, "percentage": 80.0},
      {"option_id": "opt_3", "count": 3, "percentage": 6.0},
      {"option_id": "opt_4", "count": 2, "percentage": 4.0}
    ],
    "total_responses": 50
  },
  "last_updated": "2026-01-27T11:15:00Z"
}
```

---

## Join Codes (Test)

| Join Code | Session ID | Status | Notes |
|-----------|------------|--------|-------|
| ABC123 | sess_xyz123 | ACTIVE | Valid test session |
| XYZ789 | sess_abc456 | ENDED | Expired session |
| INVALID | — | — | Invalid code |
| TEST01 | sess_test01 | CREATED | Not yet started |

---

## Database Seed Data (SQL)

### Seed Test User
```sql
INSERT INTO users (user_id, email, password_hash, full_name, created_at, updated_at)
VALUES (
  'usr_test123',
  'host@example.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU.rOp8J3rii',  -- password123
  'Test Host',
  NOW(),
  NOW()
);
```

### Seed Test Quiz
```sql
INSERT INTO quizzes (quiz_id, host_id, title, description, status, created_at, updated_at)
VALUES (
  'qz_test789',
  'usr_test123',
  'Sample Quiz',
  'Test quiz for development',
  'READY',
  NOW(),
  NOW()
);
```

### Seed Test Question
```sql
INSERT INTO questions (question_id, quiz_id, question_text, order_index, correct_option_id, created_at, updated_at)
VALUES (
  'q_test456',
  'qz_test789',
  'What is 2+2?',
  1,
  'opt_test2',
  NOW(),
  NOW()
);
```

### Seed Test Options
```sql
INSERT INTO options (option_id, question_id, option_text, order_index, created_at)
VALUES
  ('opt_test1', 'q_test456', '3', 1, NOW()),
  ('opt_test2', 'q_test456', '4', 2, NOW()),
  ('opt_test3', 'q_test456', '5', 3, NOW()),
  ('opt_test4', 'q_test456', '6', 4, NOW());
```

---

## Python Fixtures (pytest)

```python
# tests/fixtures.py
import pytest
from backend.models import User, Quiz, Question, Option, QuizSession
from backend.database import SessionLocal
import bcrypt

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def test_user(db_session):
    password_hash = bcrypt.hashpw("password123".encode(), bcrypt.gensalt(12)).decode()
    user = User(
        user_id="usr_test123",
        email="host@example.com",
        password_hash=password_hash,
        full_name="Test Host"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_quiz(db_session, test_user):
    quiz = Quiz(
        quiz_id="qz_test789",
        host_id=test_user.user_id,
        title="Sample Quiz",
        description="Test quiz",
        status="READY"
    )
    db_session.add(quiz)
    db_session.commit()
    return quiz

@pytest.fixture
def test_question(db_session, test_quiz):
    question = Question(
        question_id="q_test456",
        quiz_id=test_quiz.quiz_id,
        question_text="What is 2+2?",
        order_index=1
    )
    db_session.add(question)
    db_session.commit()
    
    options = [
        Option(option_id="opt_test1", question_id=question.question_id, option_text="3", order_index=1),
        Option(option_id="opt_test2", question_id=question.question_id, option_text="4", order_index=2),
        Option(option_id="opt_test3", question_id=question.question_id, option_text="5", order_index=3),
        Option(option_id="opt_test4", question_id=question.question_id, option_text="6", order_index=4),
    ]
    db_session.add_all(options)
    question.correct_option_id = "opt_test2"
    db_session.commit()
    return question
```

---

## Frontend Mock Data (TypeScript)

```typescript
// tests/fixtures.ts
export const mockUser = {
  user_id: 'usr_test123',
  email: 'host@example.com',
  full_name: 'Test Host'
};

export const mockQuiz = {
  quiz_id: 'qz_test789',
  title: 'Sample Quiz',
  description: 'Test quiz',
  status: 'READY',
  question_count: 1,
  created_at: '2026-01-27T10:00:00Z'
};

export const mockQuestion = {
  question_id: 'q_test456',
  text: 'What is 2+2?',
  options: [
    { option_id: 'opt_test1', text: '3' },
    { option_id: 'opt_test2', text: '4' },
    { option_id: 'opt_test3', text: '5' },
    { option_id: 'opt_test4', text: '6' }
  ],
  correct_option_id: 'opt_test2'
};

export const mockSession = {
  session_id: 'sess_xyz123',
  quiz_id: 'qz_test789',
  join_code: 'ABC123',
  status: 'ACTIVE',
  participant_count: 50
};
```
