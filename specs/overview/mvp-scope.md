# MVP Scope — Quiz-First (Single Source of Truth)

## MVP Objective

Define the minimum set of features required to deliver an end-to-end, usable **Interactive Quiz experience** for live audiences, while preserving architectural integrity and future extensibility.

This MVP is intentionally narrow and focuses on **value delivery**, not feature completeness.

---

## What's In Scope (MVP)

### Quiz Builder Flow (Host Authoring)
- Host can create new quiz (DRAFT status)
- Host can edit quiz title and description
- Host can add/edit/delete questions (MCQ only, 4 options each)
- Host can mark one correct answer per question
- Host can preview quiz before publishing
- Host can save changes (autosaved periodically)
- Host can validate quiz (enforces required fields)
- Host can publish quiz (transition to READY status)
- Host can reorder questions (drag-and-drop)

### Quiz Session Flow (Host Control)
- Host can start quiz manually and generate join code
- Host can advance to next question sequentially (one at a time)
- Host can view live answer counts/percentages during session
- Host can reveal correct answer after question closes
- Host can end quiz manually
- Platform aggregates answers per question (read-only in MVP)

### Audience Participation Flow
- Audience can join via code/link (anonymous, no login)
- Audience can view active question in real-time
- Audience can submit answer (one submission per question, no changes)
- Audience sees confirmation after submission
- Audience views correct answer after question closes
- Audience can see final results when quiz ends

### Technical Scope
- **Backend**: FastAPI + SQLAlchemy 2.0 + Pydantic
- **Database**: MySQL (AWS RDS) for persistence, Redis (local) for live state
- **Frontend**: React + Ant Design + Redux Toolkit
- **Deployment**: Docker + Docker Compose + Nginx on OCI VM (Ubuntu 24.04)
- **Authentication**: JWT-based for hosts, anonymous for audience
- **Realtime**: WebSocket or polling (to be finalized in api-contracts.md)

### Architecture Decisions (Locked)
- **Modular monolith** — single deployable application
- **3-layer architecture** — Services, Platform Kernel, Features
- **Single-tenant MVP** — tenant structure present but not enforced
- **Single VM deployment** — OCI Free Tier instance
- **MySQL on AWS RDS** — production database
- **Redis on local VM** — ephemeral live state

---

## What's Out of Scope (MVP)

### Features Explicitly Excluded
- Co-host / co-editing collaboration (single host per quiz)
- Quiz templates or cloning
- Folders or organization
- Versioning quiz definitions
- Multi-select questions
- Media uploads (images/video)
- Timers or auto-advance per question
- Leaderboards or scoring system
- Answer changes after submission
- Historical analytics dashboard
- Question history view
- Multiple active questions
- Back/skip navigation during session
- Quiz settings (shuffle, randomize options)
- Question settings (individual timers)

### Technical Exclusions
- Microservices architecture
- Kubernetes orchestration
- Managed cloud services (beyond RDS)
- Message brokers (Kafka, RabbitMQ)
- AI in core execution paths
- SSO / OAuth (MVP uses simple email+password)
- Multi-factor authentication
- Advanced profanity moderation (planned for post-MVP)

### Deployment Exclusions
- Multi-region deployment
- CDN for static assets
- Auto-scaling infrastructure
- CI/CD pipelines (manual deployment for MVP)
- Monitoring dashboards (basic logging only)

---

## MVP Functional Scope Table

| Category | Primary Actor | Feature | Description | In-Scope | Out-of-Scope |
|--------|---------------|---------|-------------|---------|--------------|
| Quiz Authoring | Host | Create quiz | Create a logical container for a quiz session | Create quiz with title and description | Templates, folders |
| Quiz Authoring | Host | Add question | Add a question to a quiz | Single-choice MCQ with 4 options | Multi-select, media |
| Quiz Authoring | Host | Define correct answer | Mark the correct option for a question | One correct answer per question | Partial scoring |
| Quiz Authoring | Host | Save quiz | Persist quiz for reuse | Manual save + autosave draft | Versioning |
| Quiz Authoring | Host | Reorder questions | Move questions up/down in sequence | Drag-and-drop reorder | Nested questions |
| Quiz Authoring | Host | Preview quiz | View quiz as it will appear | Read-only preview mode | Branching |
| Quiz Authoring | Host | Validate quiz | Check quiz completeness | Enforce required fields | Conditional logic |
| Quiz Authoring | Host | Publish quiz | Mark quiz ready for live play | Transition to READY status | Scheduled publishing |
| Quiz Session Control | Host | Start quiz | Start a live quiz session | Manual start with join code | Scheduling |
| Quiz Session Control | Host | Advance question | Move quiz to next question | Sequential flow | Back/skip |
| Quiz Session Control | Host | View results | See live answer distribution | Bar chart / counts | Leaderboards |
| Quiz Session Control | Host | Reveal answer | Show correct option to audience | Reveal after close | Partial credit |
| Quiz Session Control | Host | End quiz | End the active quiz session | Manual end | Auto-end timer |
| Audience Participation | Audience | Join quiz | Join an active quiz session | Anonymous join via code/link | Login required |
| Audience Participation | Audience | View question | See the currently active question | Real-time view | Question history |
| Audience Participation | Audience | Submit answer | Submit answer to active question | One submission per question | Answer change |
| Audience Participation | Audience | Submission feedback | Acknowledge answer submission | Confirmation message | Rankings |
| Audience Participation | Audience | View correct answer | See answer after question closes | Revealed by host | Instant reveal |
| Live Results | Platform | Aggregate answers | Aggregate responses per option | Count / percentage | Weighting |
| Realtime | Platform | Broadcast question | Push question to participants | Poll-based or WebSocket | Offline sync |
| Realtime | Platform | Broadcast results | Push result updates | Poll-based or WebSocket | Guaranteed ordering |
| Tenant Context | Platform | Resolve tenant | Resolve runtime tenant context | Single tenant | Tenant admin |
| Security | Platform | Protect host actions | Restrict host-only operations | JWT auth | SSO, MFA |
| Security | Platform | Scope audience access | Restrict access to session | Session-bound | Roles |

---

## Key Decisions & Rationale

### Why Quiz-First?
- Quizzes provide clear value (learning, engagement)
- State model is well-defined (questions → answers → results)
- Realtime requirements are explicit
- Testability is high (deterministic outcomes)

### Why Single VM?
- Simplifies MVP deployment
- Reduces operational complexity
- Sufficient for pilot scale (500-1000 users)
- Architecture supports future scaling

### Why MySQL on RDS?
- Production-grade reliability
- Managed backups and updates
- Familiar relational model
- Supports future multi-tenant growth

### Why Redis Local?
- Fast ephemeral state storage
- Session management
- Live quiz state caching
- Can be externalized later

### Why No Microservices?
- MVP does not require independent scaling
- Modular monolith preserves boundaries without operational overhead
- Can extract services later if needed

---

## Assumptions

1. **Single Tenant**: MVP runs as single-tenant system with multi-tenant structure dormant
2. **Anonymous Audience**: No audience authentication required
3. **Manual Control**: Host manually starts, advances, and ends quiz
4. **Sequential Questions**: Only one question active at a time
5. **No Offline Support**: Requires active internet connection
6. **No Historical Data**: Focus on live sessions, not analytics
7. **Basic Security**: JWT auth for hosts, no SSO or MFA
8. **Polling or WebSocket**: Realtime method to be finalized based on simplicity

---

## Non-Goals (Explicit)

- Multi-tenant administration
- Billing or subscription management
- Advanced analytics or reporting
- Integration with Zoom, Slack, etc.
- Mobile native apps
- Offline mode or progressive web app
- Internationalization (English only)
- Accessibility compliance (WCAG)
- Performance optimization beyond NFR targets

---

## References

- [Docs/000_scope.md](../../Docs/000_scope.md) — Original project scope
- [Docs/mvp-features.md](../../Docs/mvp-features.md) — Feature matrix
- [Docs/logical_architecture.md](../../Docs/logical_architecture.md) — 3-layer architecture
- [Docs/quiz-feature-internals.md](../../Docs/quiz-feature-internals.md) — Quiz state model
