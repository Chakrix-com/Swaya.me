## Goal

Build a slido.com-like interactive quiz system to build an **end-to-end flow**.

This is for production deployment.

Focus on:
- correctness
- clarity
- architectural discipline
- user experience
---

## Scope (Strict)

### Include
- Host/Admin flow (authenticated)
- Audience flow (anonymous)
- Quiz
- Question - MCQ, word cloud, polls etc
- Live Session
- Round of Answer Submission
- Deployment
- Nginx
- Redis
- Testing
- Styling polish
- Multiple questions
- Leaderboards
- Scheduling
- Analytics
- Multi-tenant logic
- Production-grade security
---

## Architecture Constraints

To be Decided:
Follow a **modular monolith** approach:

- Single backend application
- Clear internal boundaries
- No microservices

Logical layers:
- API layer (request handling only)
- Platform kernel (orchestration only)
- Application features (business logic only)

Rules:
- API does NOT contain business logic
- Platform does NOT contain feature logic
- Feature does NOT manage auth or transport

---

## Technology Stack (Use exactly)

### Backend
- FastAPI
- Pydantic
- SQLAlchemy 2.0
- SQLite (instead of MySQL, for prototype)
- JWT-based authentication (simple)

### Frontend
- React
- Ant Design (basic components only)
- Local component state (Redux NOT required for prototype)

---

## Authentication (Minimal)

- Host/Admin:
  - Email + password
  - JWT-based login
  - Auth required for host actions

- Audience:
  - Anonymous
  - Session-bound via join code
  - No login

No roles beyond Host vs Audience.

---

## Functional Flow to Implement

### Host Flow
1. Login
2. Create a quiz (title only)
3. Add one MCQ question with 4 options and 1 correct answer
4. Start quiz session
5. See join code
6. See live answer counts

### Audience Flow
1. Enter join code
2. View active question
3. Submit one answer
4. See confirmation

---

## Realtime Behavior (Simplified)

Do NOT use WebSockets.

Simulate live behavior using:
- polling
- or simple refresh-based state

Correctness > real-time fidelity.

---

## Output Expectations

Produce:
- Backend code (FastAPI app with clear modules)
- Frontend code (basic React pages)
- Clear folder structure
- Minimal comments explaining boundaries

Do NOT deploy.
Do NOT optimize.
Do NOT add tests.

Stop once the end-to-end flow works conceptually.
## UI Expectation (Important)

The prototype MUST include a runnable frontend with visible screens.

At minimum, implement:
- A Host login screen
- A Host dashboard screen
- An Audience join screen
- An Audience question screen

Navigation can be simple (buttons or links).
Visual polish is not required.


---
Business Scope - Ruchi
UI Requirement - Ruchi
Logical architecture - Nishant
Technology stack - 
User Journeys - Nishant
Non Functional Requirements - Vinay
