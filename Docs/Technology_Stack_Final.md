# Technology Stack

## Technology Philosophy

**100% Open Source & Free Technologies**

All technologies in this stack are:
- **Open source** with permissive licenses (MIT, Apache 2.0, BSD, or similar)
- **Free to use** with no licensing costs or usage limits
- **Community-driven** with active development and support
- **Production-ready** with proven track records at scale
- **Vendor-neutral** avoiding lock-in to proprietary platforms

**Exception**: Oracle Cloud Infrastructure (OCI) is used for cloud hosting due to generous free tier and cost-effectiveness, but the application remains portable to any Linux environment.

---

## Table 1: High-Level Technology Stack (Quick Reference)

| Tech Component | License | Layer / Responsibility | Quality | Time to Build | Ease to Manage | Performance | Weight |
|---|---|---|---|---|---|---|---|
| React | MIT | Frontend UI framework | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| Ant Design (AntD) | MIT | Unified UI component system | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Medium-Heavy |
| Redux Toolkit (RTK) | MIT | Global application state management | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medium |
| FastAPI | MIT | Backend application framework | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Light |
| Pydantic | MIT | Data validation & serialization | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| SQLAlchemy 2.0 | MIT | ORM and data access layer | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Medium |
| Alembic | MIT | Database schema migrations | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | N/A | Light |
| MySQL | GPL v2 | Persistent relational database | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medium |
| Redis | BSD 3-Clause | Cache and ephemeral runtime state | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Light |
| PyJWT | MIT | JWT token generation & validation | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| bcrypt | Apache 2.0 | Password hashing | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| Slowapi | MIT | Application-level rate limiting | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Light |
| python-json-logger | BSD 2-Clause | Structured JSON logging | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| better-profanity | MIT | Profanity detection & filtering | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| bleach | Apache 2.0 | HTML/text sanitization | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| python-statemachine | MIT | State transition management | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| React Hook Form | MIT | Form state management | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Light |
| Yup | MIT | Schema validation | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| Font Awesome | MIT/CC BY 4.0 | Icon library | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| date-fns | MIT | Date/time utilities | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| pytest-asyncio | Apache 2.0 | Async test support | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | N/A | Light |
| Docker | Apache 2.0 | Build and deployment packaging | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | N/A | Medium |
| Nginx | BSD 2-Clause | Reverse proxy and traffic routing | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Light |

## Table 2: Functional Responsibility & Implementation Guidance

**All components listed are open source with permissive licenses.**

| Tech Component | Functional Responsibility |
|---|---|
| React | Component-level local UI state, forms, modals, UI-only interactions |
| Ant Design (AntD) | Reusable UI components for Audience, Host, and Admin |
| Redux Toolkit (RTK) | Global state: session context, auth state, live poll/quiz data |
| FastAPI | Core backend runtime and internal orchestration |
| FastAPI (REST) | Auth, setup/configuration, history, analytics APIs |
| FastAPI (WebSocket) | Live sessions, active rooms, real-time counters |
| Pydantic | Request/response schemas and WebSocket payload validation |
| SQLAlchemy 2.0 | Persistent data access and domain modeling |
| Alembic | Controlled database schema evolution |
| MySQL | Durable storage for sessions, polls, votes, analytics |
| Redis | Ephemeral live state, counters, rate limiting |
| JWT Auth | Role-based access control (Admin / Host / Audience) |
| Slowapi | Context-aware rate limiting (per-IP, per-participant, per-endpoint) |
| python-json-logger | Structured logging for API analytics, audit trails, monitoring |
| better-profanity | Profanity detection for all user-generated text (questions, answers, names) |
| bleach | Sanitize user input to prevent XSS attacks and injection |
| python-statemachine | Enforce quiz session state transitions (CREATED → ACTIVE → ENDED) |
| React Hook Form | Efficient form state management with validation (login, quiz builder) |
| Yup | Schema-based validation for forms (email format, required fields) |
| Font Awesome | Consistent icon set for UI actions and status indicators |
| date-fns | Format timestamps and relative time display (e.g., "2 mins ago") |
| pytest-asyncio | Unit test async FastAPI endpoints and coroutines |
| Docker | Consistent environments across dev, test, prod |
| Nginx | Routing and proxying for REST and WebSocket traffic, edge-level rate limiting |