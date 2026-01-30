# Swaya.me Specifications

This directory contains the complete, AI-oriented specifications for the Swaya.me interactive quiz platform MVP.

**Technology Commitment:** 100% open source and free software stack (MIT, Apache 2.0, BSD, GPL licenses). Zero licensing costs. Full portability. No vendor lock-in.

📖 **See [TECHNOLOGY_REFERENCE.md](./TECHNOLOGY_REFERENCE.md) for complete technology stack details.**

---

## Directory Structure

```
specs/
├── overview/           # Vision, scope, personas
├── architecture/       # Logical design, deployment, data flow
├── backend/           # API contracts, domain model, persistence, auth, realtime
├── frontend/          # Screens, state management, UI flows
├── runtime/           # Configuration, ops runbook, dev environment
└── qa/                # Acceptance criteria, test plan, fixtures
```

---

## Overview

High-level vision, scope, and user personas.

| File | Purpose |
|------|---------|
| [vision.md](./overview/vision.md) | Product vision, goals, and success criteria |
| [mvp-scope.md](./overview/mvp-scope.md) | Single source of truth for MVP scope and decisions |
| [personas.md](./overview/personas.md) | User roles (Host, Audience) and capabilities |
| [multi-tenant-saas-architecture.md](./overview/multi-tenant-saas-architecture.md) | Multi-tenant tier system overview and design |

---

## Architecture

Logical architecture, deployment model, and data flows.

| File | Purpose |
|------|---------|
| [logical-architecture.md](./architecture/logical-architecture.md) | 3-layer architecture (Core, Broker, Features) |
| [deployment.md](./architecture/deployment.md) | Single-VM deployment on OCI |
| [data-flow.md](./architecture/data-flow.md) | Sequence diagrams for join, submit, results |

---

## Backend

API specifications, domain models, and backend design.

| File | Purpose |
|------|---------|
| [api-contracts.md](./backend/api-contracts.md) | REST API endpoints, payloads, errors (11 endpoints including quiz builder) |
| [api-layer-strategy.md](./backend/api-layer-strategy.md) | Rate limiting, logging, profanity filtering, analytics (3-tier: Nginx + Slowapi + Redis) |
| [domain-model.md](./backend/domain-model.md) | Entities, relationships, business rules (with tenant scoping) |
| [persistence.md](./backend/persistence.md) | Database schema, tables, migrations (MySQL) |
| [auth.md](./backend/auth.md) | JWT authentication, authorization model |
| [realtime.md](./backend/realtime.md) | Polling vs WebSocket strategy |
| [quiz-builder.md](./backend/quiz-builder.md) | Quiz builder feature, autosave, validation, publishing |
| [tier-management.md](./backend/tier-management.md) | Tier enforcement, quota tracking, entitlements (Core + Broker integration) |
| [multi-tenant-isolation.md](./backend/multi-tenant-isolation.md) | Data isolation strategy, query scoping, cross-tenant prevention |
| [tier-configuration.md](./backend/tier-configuration.md) | Tier definitions, feature matrix, quota types, enforcement points |

---

## Frontend

UI screens, state management, and user flows.

| File | Purpose |
|------|---------|
| [screens.md](./frontend/screens.md) | Screen-by-screen UI definitions with fields and validation |
| [state.md](./frontend/state.md) | Redux Toolkit slices, actions, selectors |
| [ui-flows.md](./frontend/ui-flows.md) | End-to-end user journeys (Host, Audience) |

---

## Runtime

Configuration, operations, and development environment setup.

| File | Purpose |
|------|---------|
| [config.md](./runtime/config.md) | Environment variables, Docker Compose, Nginx |
| [ops-runbook.md](./runtime/ops-runbook.md) | Deployment steps, maintenance tasks, troubleshooting |
| [dev-env.md](./runtime/dev-env.md) | Local development setup (Python, Node, Docker) |

---

## QA

Testing strategy, acceptance criteria, and test fixtures.

| File | Purpose |
|------|---------|
| [acceptance.md](./qa/acceptance.md) | Acceptance criteria per feature (done criteria) |
| [test-plan.md](./qa/test-plan.md) | Testing strategy, coverage goals, test types |
| [fixtures.md](./qa/fixtures.md) | Sample payloads, seed data, mock objects |

---

## How to Use These Specs

### For Developers
1. Start with [mvp-scope.md](./overview/mvp-scope.md) to understand what's in/out of scope
2. Review [logical-architecture.md](./architecture/logical-architecture.md) for system design
3. Refer to [api-contracts.md](./backend/api-contracts.md) for API endpoints
4. Use [domain-model.md](./backend/domain-model.md) for database entities
5. Follow [dev-env.md](./runtime/dev-env.md) for local setup
6. Implement per [acceptance.md](./qa/acceptance.md) done criteria

### For AI Agents
- Specs are **single-purpose and concise**
- Each file is the **source of truth** for its domain
- Key decisions are **normalized in mvp-scope.md** and referenced elsewhere
- API contracts include **concrete examples** (request/response)
- Fixtures include **sample payloads** for bootstrapping
- No conflicts or ambiguities

### For Project Managers
- [mvp-scope.md](./overview/mvp-scope.md) defines what's included/excluded
- [acceptance.md](./qa/acceptance.md) defines done criteria per feature
- [test-plan.md](./qa/test-plan.md) defines quality expectations

### For Designers
- [screens.md](./frontend/screens.md) defines UI fields and validation
- [ui-flows.md](./frontend/ui-flows.md) defines user journeys
- [personas.md](./overview/personas.md) defines user roles

---

## Authoring Principles

These specs follow the principles defined in [Docs/specs-structure.md](../Docs/specs-structure.md):

1. **Single-purpose**: Each file covers one domain
2. **Concise**: No unnecessary verbosity
3. **Source of truth**: No conflicting information
4. **AI-ready**: Concrete examples, tables, diagrams
5. **Normalized decisions**: Key choices in mvp-scope.md

---

## Migration from Docs/

The original [Docs/](../Docs/) folder contained planning documents that have been reorganized into this `specs/` structure:

- **Docs/000_scope.md** → [overview/mvp-scope.md](./overview/mvp-scope.md)
- **Docs/logical_architecture.md** → [architecture/logical-architecture.md](./architecture/logical-architecture.md)
- **Docs/mvp-features.md** → [overview/mvp-scope.md](./overview/mvp-scope.md) (integrated)
- **Docs/quiz-feature-internals.md** → [backend/domain-model.md](./backend/domain-model.md)
- **Docs/auth.md** → [backend/auth.md](./backend/auth.md)
- **Docs/business_scope.md** → [overview/vision.md](./overview/vision.md)
- **Docs/UI_Requirements.md** → [frontend/screens.md](./frontend/screens.md)
- **Docs/audience-join-quiz.md** → [architecture/data-flow.md](./architecture/data-flow.md)
- **Docs/devops-stack.md** → [architecture/deployment.md](./architecture/deployment.md)

---

## Status

| Section | Status | Notes |
|---------|--------|-------|
| Overview | ✅ Complete | Vision, scope, personas defined |
| Architecture | ✅ Complete | Logical, deployment, data flows |
| Backend | ✅ Complete | API contracts, domain model, persistence, auth, realtime |
| Frontend | ✅ Complete | Screens, state, UI flows |
| Runtime | ✅ Complete | Config, ops, dev env |
| QA | ✅ Complete | Acceptance, test plan, fixtures |

---

## Next Steps

1. **Implementation**: Follow specs to build backend and frontend
2. **Testing**: Use [qa/test-plan.md](./qa/test-plan.md) and [qa/fixtures.md](./qa/fixtures.md)
3. **Deployment**: Follow [runtime/ops-runbook.md](./runtime/ops-runbook.md)
4. **Feedback Loop**: Update specs as decisions evolve

---

## Related Documents

- [Docs/specs-structure.md](../Docs/specs-structure.md) — Authoring guidance for AI-oriented specs
- [Docs/issues.md](../Docs/issues.md) — Known documentation issues (now resolved)
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) — AI agent instructions

---

## Maintenance

Specs are living documents. When making changes:

1. Update the relevant spec file
2. Ensure consistency across related files (e.g., if API contract changes, update data-flow.md)
3. Update this README if new sections are added
4. Keep [mvp-scope.md](./overview/mvp-scope.md) as the single source of truth for scope decisions
