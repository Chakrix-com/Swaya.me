# Swaya.me Implementation Plan

## Problem Statement
Build the MVP of Swaya.me - an interactive quiz platform (Slido-like) with multi-tenant SaaS architecture using 100% open source technologies. The system follows a 3-layer architecture (Core, Broker, Features) and must support host authoring, audience participation, and live quiz sessions.

## Proposed Approach
Implement a modular monolith with strict separation of concerns:
1. Backend (FastAPI + SQLAlchemy + MySQL + Redis)
2. Frontend (React + Ant Design + Redux Toolkit)
3. Docker-based deployment with Nginx

Follow test-driven development and implement features incrementally according to the 3-layer model.

---

## Implementation Workplan

### Phase 1: Project Scaffolding & Infrastructure
- [ ] Create backend project structure (core, broker, features)
- [ ] Set up FastAPI application with basic configuration
- [ ] Create database models for multi-tenant architecture
- [ ] Set up Alembic for database migrations
- [ ] Configure SQLAlchemy 2.0 with async support
- [ ] Create Docker Compose setup for local development
- [ ] Set up Redis connection and utilities
- [ ] Create frontend project with React + Vite
- [ ] Configure Ant Design and Redux Toolkit
- [ ] Set up basic routing structure

### Phase 2: Core Layer (Platform Foundation)
- [ ] Implement authentication system (JWT-based)
- [ ] Create user registration and login endpoints
- [ ] Implement multi-tenant isolation at database level
- [ ] Create tenant management services
- [ ] Implement tier configuration system
- [ ] Set up logging, auditing, and observability
- [ ] Create shared utilities and helpers

### Phase 3: Broker Layer (Policy & Orchestration)
- [ ] Implement API Gateway pattern
- [ ] Create input validation middleware
- [ ] Implement rate limiting (Nginx + Slowapi + Redis)
- [ ] Set up profanity filter integration
- [ ] Create policy enforcement middleware
- [ ] Implement tier-based quota checking
- [ ] Set up WebSocket/polling infrastructure for realtime

### Phase 4: Quiz Feature (Business Logic)
- [ ] Create quiz domain models (Quiz, Question, Answer)
- [ ] Implement quiz builder CRUD operations
- [ ] Create question management (add, edit, delete, reorder)
- [ ] Implement quiz validation logic
- [ ] Create quiz state machine (DRAFT → READY → ACTIVE → ENDED)
- [ ] Implement session management
- [ ] Create answer submission logic (one per participant per question)
- [ ] Build answer aggregation and statistics
- [ ] Implement result calculation

### Phase 5: API Implementation
- [ ] Implement Auth endpoints (/auth/login, /auth/register)
- [ ] Implement Quiz Builder endpoints (CRUD)
- [ ] Implement Session endpoints (start, advance, end)
- [ ] Implement Audience endpoints (join, submit answer)
- [ ] Implement Results endpoints (aggregation, final results)
- [ ] Add API documentation with OpenAPI/Swagger

### Phase 6: Frontend - Host Dashboard
- [ ] Create login/registration screens
- [ ] Build quiz list view (dashboard)
- [ ] Create quiz builder interface
- [ ] Implement question editor (add/edit/delete/reorder)
- [ ] Build quiz preview screen
- [ ] Create quiz control panel (start, advance, end)
- [ ] Implement live results dashboard

### Phase 7: Frontend - Audience Experience
- [ ] Create join screen (code/link entry)
- [ ] Build waiting room screen
- [ ] Implement question display screen
- [ ] Create answer submission interface
- [ ] Build answer confirmation screen
- [ ] Implement results display screen

### Phase 8: Realtime Communication
- [ ] Set up WebSocket server infrastructure
- [ ] Implement connection management
- [ ] Create event broadcasting system
- [ ] Implement question push to audience
- [ ] Create live answer aggregation updates
- [ ] Implement result broadcasting

### Phase 9: Testing & Quality Assurance
- [ ] Write unit tests for Core layer
- [ ] Write unit tests for Quiz feature
- [ ] Create integration tests for API endpoints
- [ ] Build end-to-end tests for critical flows
- [ ] Test multi-tenant isolation
- [ ] Test tier enforcement and quotas
- [ ] Perform load testing

### Phase 10: Deployment & DevOps
- [ ] Create production Docker Compose configuration
- [ ] Set up Nginx reverse proxy configuration
- [ ] Configure SSL/TLS certificates
- [ ] Create deployment scripts
- [ ] Set up database backup strategy
- [ ] Create monitoring and alerting setup
- [ ] Write operations runbook

---

## Notes & Considerations

### Architecture Constraints
- Strict 3-layer separation: Core → Broker → Features
- Features NEVER call services directly
- Platform contains NO feature-specific logic
- All business logic in Features layer
- Multi-tenant isolation at every layer

### Technology Stack (100% Open Source)
- Backend: FastAPI (MIT), SQLAlchemy 2.0 (MIT), Pydantic (MIT)
- Database: MySQL 8.0+ (GPL v2), Redis (BSD)
- Frontend: React (MIT), Ant Design (MIT), Redux Toolkit (MIT)
- Deployment: Docker (Apache 2.0), Nginx (BSD)
- Auth: PyJWT (MIT), bcrypt (Apache 2.0)

### Key Design Decisions
- **Modular Monolith**: Single deployable, future microservices-ready
- **Quiz State Machine**: CREATED → ACTIVE → QUESTION_CLOSED → ENDED
- **Answer Submission**: One per participant per question, no changes
- **Anonymous Audience**: No login required, session-bound
- **Tier-Based Limits**: Free (50 participants, 10 questions), Pro (1000 participants, 100 questions)

### Out of Scope (MVP)
- Multi-select questions
- Media uploads
- Timers/auto-advance
- Leaderboards/scoring
- Answer changes
- Historical analytics
- Quiz templates
- SSO/OAuth (simple email+password only)

### Risk Mitigation
- Start with database schema and migrations
- Test multi-tenant isolation early
- Validate tier enforcement before features
- Keep WebSocket implementation simple (fallback to polling if needed)
- Focus on happy path first, edge cases later

### Success Criteria
- Host can create quiz with 10 questions
- Host can start quiz and generate join code
- 50 anonymous participants can join
- All can submit answers and see results in real-time
- System enforces tier limits correctly
- All data properly isolated by tenant

---

## Current Status
**Phase**: Phase 2 Complete - Core Layer Implemented  
**Next Action**: Implement Quiz Feature (CRUD operations, session management, answer submission)

---

## Completed Work

### Phase 1: Project Scaffolding ✅ (100%)
- Backend 3-layer structure (38 Python files)
- FastAPI application with CORS and middleware
- SQLAlchemy 2.0 models (multi-tenant architecture)
- Alembic migrations setup
- Docker Compose (MySQL + Redis + Backend + Frontend)
- Requirements and environment configuration

### Phase 2: Core Layer ✅ (100%)
**Authentication System:**
- JWT token creation and verification
- Password hashing with bcrypt
- User registration with tenant creation
- User login endpoint
- Protected route authentication
- CurrentUser context with tenant info

**Multi-Tenant Architecture:**
- Tenant model with tier assignment
- Automatic tenant isolation in queries
- Tenant context middleware
- Slug generation for tenant URLs

**Tier Management:**
- Tier configuration (Free, Pro, Enterprise)
- Quota enforcement service
- Participant/question/event limits
- Redis-backed counters

**Infrastructure:**
- Redis client with connection pooling
- Structured logging (JSON for production)
- Custom exception hierarchy
- Database seeding scripts
- Setup automation script

**API Endpoints Implemented:**
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me

### Database Schema
**Core Tables:**
- tenants (id, name, slug, tier, is_active)
- users (id, tenant_id, email, hashed_password, full_name)
- events (id, tenant_id, creator_id, title, description, join_code)
- tier_configurations (tier, max_participants, max_questions, max_concurrent_events)

**Quiz Tables:**
- quizzes (id, tenant_id, event_id, title, description, status)
- questions (id, quiz_id, text, order, options, correct_answer_index)
- quiz_sessions (id, tenant_id, quiz_id, status, current_question_index)
- participants (id, session_id, display_name, session_token)
- answers (id, session_id, participant_id, question_id, selected_option_index, is_correct)
