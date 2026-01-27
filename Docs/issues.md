# Documentation Issues

- Stack conflicts: SQLite prototype vs MySQL; polling-only realtime vs WebSockets/SSE; "no tests" vs 70% coverage; "do not deploy" vs deployment plans.
- Scope ambiguity: MVP is narrow (single quiz, polling) but other docs describe parity features (moderation, multi-tenancy, analytics, presenter mode, word clouds, surveys), creating scope creep risk.
- Missing contracts: No concrete API spec (routes, payloads, errors), DB schema/ERD, DTOs, join-code lifecycle, or JWT claim/expiry details.
- Frontend gaps: Required screens listed but no wireframes/IA, field lists, or navigation flows to guide implementation.
- Realtime/polling undefined: Poll intervals, payload shapes, state/cache boundaries, and degradation behavior unspecified while WebSockets are disallowed in MVP.
- Config/ops omissions: No env var contract, bootstrap/runbook, or pairing instructions for Docker/Nginx/Redis/RDS expectations.
- Testing ambiguity: MVP says skip tests, NFRs require 70% coverage and test types—quality gates unclear.
- Multi-tenancy vs single-tenant: MVP assumes single-tenant/anonymous audience, but other docs add tenant contexts and SaaS tiers without a first-build decision.
