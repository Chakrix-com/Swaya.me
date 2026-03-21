# Test Plan (MVP)

This document defines the testing strategy, test types, and quality expectations for the Swaya.me MVP.

---

## Testing Philosophy

**Core Principles**:
- **Correctness over speed**: Prioritize accurate state management and data handling
- **Happy path first**: Ensure core flows work flawlessly before edge cases
- **Testability by design**: Features must be testable in isolation
- **Pragmatic coverage**: Focus on critical paths, not 100% coverage

**MVP Testing Scope**:
- Unit tests for business logic
- Integration tests for API endpoints
- Manual UI testing (automated E2E tests post-MVP)
- Load testing for performance validation

---

## Test Coverage Goals

| Layer | Target Coverage | Priority |
|-------|-----------------|----------|
| **Backend Business Logic** | 70%+ | High |
| **Backend API Endpoints** | 60%+ | High |
| **Frontend Components** | 50%+ | Medium |
| **Frontend State Management** | 60%+ | High |
| **End-to-End Flows** | Manual | High |

---

## Test Types

### 1. Unit Tests

**Purpose**: Verify individual functions, methods, and components in isolation.

**Scope**:
- Domain model validation
- Quiz state transitions
- Answer submission rules
- Aggregation logic
- Auth token generation/validation
- Utility functions

**Framework**:
- **Backend**: pytest
- **Frontend**: Jest + React Testing Library

**Example (Backend)**:
```python
def test_quiz_state_transition_created_to_active():
    session = QuizSession(status=SessionStatus.CREATED)
    session.start()
    assert session.status == SessionStatus.ACTIVE
    assert session.started_at is not None
```

**Example (Frontend)**:
```javascript
test('Login form validates email format', () => {
  render(<Login />);
  const emailInput = screen.getByPlaceholderText('host@example.com');
  fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
  fireEvent.blur(emailInput);
  expect(screen.getByText('Please enter a valid email')).toBeInTheDocument();
});
```

---

### 2. Integration Tests

**Purpose**: Verify interaction between components and external systems.

**Scope**:
- API endpoints (request → response)
- Database queries (SQLAlchemy models)
- Redis state management
- JWT authentication flow
- Answer aggregation from database

**Framework**:
- **Backend**: pytest with FastAPI TestClient
- **Frontend**: Jest with mock API responses

**Example (Backend)**:
```python
def test_create_quiz_endpoint(client, auth_headers):
    response = client.post(
        "/api/v1/quizzes",
        json={"title": "Test Quiz", "description": "Testing"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Quiz"
    assert data["status"] == "DRAFT"
```

**Example (Frontend)**:
```javascript
test('Dashboard fetches and displays quizzes', async () => {
  mockAxios.get.mockResolvedValueOnce({
    data: { quizzes: [{ quiz_id: 'qz_1', title: 'Quiz 1', status: 'READY' }] }
  });
  render(<Dashboard />);
  await waitFor(() => {
    expect(screen.getByText('Quiz 1')).toBeInTheDocument();
  });
});
```

---

### 3. Manual UI Testing

**Purpose**: Verify end-to-end user flows and visual correctness.

**Scope**:
- Host login and quiz creation
- Quiz builder UX (add questions, publish)
- Host session control (start, advance, end)
- Audience join and participation
- Real-time updates (polling)
- Error handling and edge cases

**Test Checklist**:
- [ ] Host can log in successfully
- [ ] Host can create and publish quiz
- [ ] Host can start quiz session and see join code
- [ ] Audience can join via join code
- [ ] Audience sees questions in real-time
- [ ] Audience can submit answers
- [ ] Host sees live answer counts
- [ ] Results are displayed correctly after question close
- [ ] Quiz can be ended gracefully
- [ ] Error messages are clear and helpful

**Tools**:
- Browser DevTools (Console, Network tab)
- Redux DevTools (state inspection)
- Manual clicks and observations

---

### 4. Load Testing

**Purpose**: Validate performance under expected load conditions.

**Scope**:
- 200 concurrent audience members per quiz session
- 5 simultaneous quiz sessions
- Answer submission throughput
- Polling load on backend
- Database query performance
- Redis cache hit rate

**Tools**:
- **Locust**: Python-based load testing framework
- **Apache Bench (ab)**: Simple HTTP benchmarking

**Example Locust Script**:
```python
from locust import HttpUser, task, between

class AudienceUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Join session
        response = self.client.post("/api/v1/sessions/join", json={"join_code": "ABC123"})
        self.participant_id = response.json()["participant_id"]
        self.session_id = response.json()["session_id"]
    
    @task
    def poll_status(self):
        self.client.get(f"/api/v1/sessions/{self.session_id}/status")
    
    @task
    def submit_answer(self):
        self.client.post(
            f"/api/v1/sessions/{self.session_id}/submit",
            json={
                "participant_id": self.participant_id,
                "question_id": "q_456",
                "option_id": "opt_2"
            }
        )
```

**Performance Targets** (from NFRs):
- API response time < 500ms (95th percentile)
- Realtime latency < 2s
- Redis cache hit rate > 95%
- Zero database connection exhaustion

---

### 5. Security Testing (Basic MVP)

**Purpose**: Verify basic security measures are in place.

**Scope**:
- JWT token validation
- Password hashing (bcrypt)
- Rate limiting (login, join, submit)
- SQL injection prevention
- XSS prevention
- CORS configuration

**Manual Tests**:
- [ ] Invalid JWT token is rejected (401 Unauthorized)
- [ ] Expired JWT token is rejected
- [ ] Passwords are never returned in API responses
- [ ] Rate limiting triggers after threshold (429 Too Many Requests)
- [ ] SQL injection attempts are blocked (parameterized queries)
- [ ] XSS attempts are sanitized (input validation)
- [ ] CORS only allows frontend domain

**Tools**:
- curl or Postman for manual API testing
- Browser DevTools (Network tab, CORS errors)

---

## Test Data & Fixtures

### Seed Data (Development/Testing)

**Test Host User**:
```json
{
  "email": "host@example.com",
  "password": "password123",
  "full_name": "Test Host"
}
```

**Test Quiz**:
```json
{
  "title": "Sample Quiz",
  "description": "Test quiz for development",
  "status": "READY",
  "questions": [
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
  ]
}
```

**Test Session**:
```json
{
  "join_code": "ABC123",
  "status": "ACTIVE"
}
```

### Fixture Files

**Backend** (tests/fixtures.py):
```python
import pytest
from backend.models import User, Quiz, Question, Option
from backend.database import SessionLocal

@pytest.fixture
def test_user(db_session):
    user = User(
        user_id="usr_test",
        email="host@example.com",
        password_hash="$2b$12$...",
        full_name="Test Host"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_quiz(db_session, test_user):
    quiz = Quiz(
        quiz_id="qz_test",
        host_id=test_user.user_id,
        title="Test Quiz",
        status="READY"
    )
    db_session.add(quiz)
    db_session.commit()
    return quiz
```

**Frontend** (tests/fixtures.ts):
```typescript
export const mockQuiz = {
  quiz_id: 'qz_test',
  title: 'Test Quiz',
  status: 'READY',
  question_count: 1,
  created_at: '2026-01-27T10:00:00Z'
};

export const mockQuestion = {
  question_id: 'q_test',
  text: 'What is 2+2?',
  options: [
    { option_id: 'opt_1', text: '3' },
    { option_id: 'opt_2', text: '4' },
    { option_id: 'opt_3', text: '5' },
    { option_id: 'opt_4', text: '6' }
  ],
  correct_option_id: 'opt_2'
};
```

---

## Test Execution

### Run Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run tests matching pattern
pytest -k "test_quiz"

# Verbose output
pytest -v
```

### Run Frontend Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test -- screens/Login.test.tsx

# Watch mode (re-run on file changes)
npm test -- --watch
```

### Run Load Tests

```bash
# Start load test with Locust
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Or via command line (headless)
locust -f tests/load/locustfile.py --host=http://localhost:8000 --users 200 --spawn-rate 10 --run-time 5m --headless
```

---

## Continuous Integration (Post-MVP)

### GitHub Actions Workflow (Example)

```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          cd backend
          pytest --cov=backend --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage
```

---

## Test Reporting

### Coverage Reports

**Backend**:
- Generate HTML report: `pytest --cov=backend --cov-report=html`
- View report: `open htmlcov/index.html`

**Frontend**:
- Generate coverage report: `npm test -- --coverage`
- View report: `open coverage/lcov-report/index.html`

### Test Metrics

Track over time:
- **Test Pass Rate**: % of tests passing
- **Code Coverage**: % of code covered by tests
- **Test Execution Time**: Time to run full test suite
- **Flaky Tests**: Tests that intermittently fail

---

## Known Limitations (MVP)

- No automated E2E tests (Selenium, Playwright)
- No visual regression testing
- No cross-browser testing (manual only)
- No mobile device testing (responsive design manual only)
- No accessibility testing (WCAG compliance post-MVP)
- No stress testing beyond 200 concurrent users per session

---

## Test Environment

### Local Development
- Backend: `localhost:8000`
- Frontend: `localhost:3000`
- MySQL: `localhost:3306`
- Redis: `localhost:6379`

### Staging (Post-MVP)
- Backend: `https://staging.swaya.me/api/v1`
- Frontend: `https://staging.swaya.me`

### Production
- Backend: `https://swaya.me/api/v1`
- Frontend: `https://swaya.me`

---

## Test Data Cleanup

### After Each Test

**Backend**:
```python
@pytest.fixture(autouse=True)
def cleanup_database(db_session):
    yield
    db_session.rollback()
    db_session.close()
```

**Frontend**:
```javascript
afterEach(() => {
  cleanup();  // React Testing Library cleanup
  jest.clearAllMocks();
});
```

### After Test Suite

```bash
# Reset database
docker-compose run backend alembic downgrade base
docker-compose run backend alembic upgrade head

# Clear Redis
docker exec -it swaya-dev-redis redis-cli FLUSHALL
```

---

## Quality Gates

Before merging to `main`:
- [ ] All tests passing
- [ ] Code coverage ≥ 70% for backend business logic
- [ ] No critical or high-priority bugs
- [ ] Code reviewed and approved
- [ ] Manual testing completed for affected flows

Before deploying to production:
- [ ] All quality gates passed
- [ ] Load testing completed (200 users per session, 5 sessions)
- [ ] Security checklist reviewed
- [ ] Deployment runbook followed
- [ ] Rollback plan documented
