# Swaya.me — AI Agent Instructions

## Project Overview
Swaya.me is a **Slido-like interactive quiz platform** being built as a **modular monolith** for production deployment. The codebase is in planning phase with comprehensive architectural documentation in `Docs/`.

**Core Goal:** Build an end-to-end live quiz system emphasizing correctness, clarity, architectural discipline, and user experience.

## Architecture: The 3-Layer Model

All code must follow this strict layering (see [Docs/logical_architecture.md](../Docs/logical_architecture.md)):

### 1. Services Layer (API + Realtime)
- **API Service:** Request/response handling only (quiz creation, joins, submissions)
- **Realtime Service:** WebSocket management and message fan-out
- **Rule:** Services translate transport into platform intent—NO business logic here

### 2. Platform Kernel
- Orchestration and policy enforcement layer
- Resolves tenant context once per request and propagates internally
- Controls quiz session lifecycle and feature orchestration
- **Rule:** Platform invokes features but contains NO feature-specific logic

### 3. Features Layer (Quiz Feature)
- Business capabilities that can evolve independently
- Quiz feature owns: definition, state, validation, aggregation
- **Rule:** Features never communicate directly with services or resolve tenant context

**Critical:** API does NOT contain business logic. Platform does NOT contain feature logic. Features do NOT manage auth or transport.

## Technology Stack (Use Exactly)

**Backend:** FastAPI + Pydantic + SQLAlchemy 2.0 + JWT auth  
**Database:** MySQL (OCI VM) for persistence, Redis (local) for live state  
**Frontend:** React + Ant Design + Redux Toolkit  
**Deployment:** Docker + Docker Compose + Nginx on OCI VM (Ubuntu 24.04)  

See [Docs/Technology_Stack_Final.md](../Docs/Technology_Stack_Final.md) for component responsibilities.

## State Management Philosophy

**Quiz Session States:** `CREATED → ACTIVE → QUESTION_CLOSED → ENDED`
- Transitions are explicit and platform-driven
- Only ONE question active at a time
- NO hidden state—all state must be explicit and observable

**Answer Submission Rules:**
- Only accepted when question state is `OPEN`
- One submission per participant per question (no changes)
- Late submissions (after close) are rejected
- Validation happens in Quiz feature, not API layer

See [Docs/quiz-feature-internals.md](../Docs/quiz-feature-internals.md) for complete state model.

## Authentication & Authorization

**Host/Admin:** Email + password, JWT-based, required for host actions  
**Audience:** Anonymous, session-bound via join code, NO login required  

No roles beyond Host vs Audience. SSO support planned but not in MVP.

## Policy Enforcement (Mandatory at Broker Layer)

ALL user-generated content passes through profanity detection BEFORE reaching features:
- Applied to: questions, answers, display names, poll options, word clouds
- Event-level modes: reject, mask, or route to moderation
- Profane content must NEVER be stored unsanitized or broadcast
- Enforcement is server-side only at the Broker layer

## MVP Feature Scope (Quiz-First)

**In Scope:**
- Create quiz with title, add MCQ questions (4 options, 1 correct)
- Start/end quiz manually, advance questions sequentially
- Anonymous audience joins via code/link
- Submit answer once per question, view correct answer after close
- Live answer aggregation (counts/percentages)
- Real-time broadcasting of questions and results

**Explicitly Out of Scope:**
- Scheduling, templates, folders, versioning
- Multi-select questions, media uploads, timers
- Leaderboards, scoring, answer changes, historical analytics
- Microservices, Kubernetes, managed cloud services, AI in core paths

See [Docs/mvp-features.md](../Docs/mvp-features.md) for detailed feature matrix.

## Testability Requirements

**Feature Layer (Quiz):**
- Must run without services, DB, or realtime (in-memory tests)
- State transitions, validation rules, aggregation must be unit-testable
- Same input must produce same output (deterministic)
- Idempotent aggregation from submissions

**Platform Separation:**
- Features are invoked by platform—never depend on transport
- Mock platform interactions during feature tests

## File Organization Patterns

When implementing, organize as:
```
backend/
  api/           # API service (transport only)
  realtime/      # WebSocket/SSE handling
  platform/      # Orchestration and policies
  features/
    quiz/        # Quiz feature (business logic)
  persistence/   # SQLAlchemy models + Alembic migrations

frontend/
  src/
    features/
      quiz/      # Quiz-specific React components
    shared/      # Reusable AntD components
    store/       # Redux Toolkit slices
```

## Key Documentation Files

- [Docs/000_scope.md](../Docs/000_scope.md) — Project scope and constraints
- [Docs/logical_architecture.md](../Docs/logical_architecture.md) — Complete 3-layer architecture
- [Docs/mvp-high-level-architecture.md](../Docs/mvp-high-level-architecture.md) — Deployment model
- [Docs/quiz-feature-internals.md](../Docs/quiz-feature-internals.md) — Quiz state machine
- [Docs/devops-stack.md](../Docs/devops-stack.md) — Infrastructure setup

## Common Pitfalls to Avoid

❌ Putting business logic in API endpoints  
❌ Features calling services directly  
❌ Platform containing feature-specific code  
❌ Storing unsanitized profane content  
❌ Allowing answer changes after submission  
❌ Multiple active questions in a session  
❌ Hidden or implicit state in features  
❌ Vendor-specific dependencies (maintain portability)  

## Development Commands

*To be populated when implementation begins. Expected:*
- Database migrations: `alembic upgrade head`
- Backend server: `uvicorn main:app --reload`
- Frontend dev: `npm run dev`
- Docker deployment: `docker-compose up`
