# Technology Stack

## Table 1: High-Level Technology Stack (Quick Reference)

| Tech Component | Layer / Responsibility | Quality | Time to Build | Ease to Manage | Performance | Weight |
|---|---|---|---|---|---|---|
| React | Frontend UI framework | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| Ant Design (AntD) | Unified UI component system | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Medium-Heavy |
| Redux Toolkit (RTK) | Global application state management | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medium |
| FastAPI | Backend application framework | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Light |
| SQLAlchemy 2.0 | ORM and data access layer | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Medium |
| Alembic | Database schema migrations | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | N/A | Light |
| MySQL | Persistent relational database | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medium |
| Redis | Cache and ephemeral runtime state | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Light |
| JWT Auth | Authentication and authorization | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Light |
| Docker | Build and deployment packaging | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | N/A | Medium |
| Nginx | Reverse proxy and traffic routing | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Light |

## Table 2: Functional Responsibility & Implementation Guidance

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
| Docker | Consistent environments across dev, test, prod |
| Nginx | Routing and proxying for REST and WebSocket traffic |