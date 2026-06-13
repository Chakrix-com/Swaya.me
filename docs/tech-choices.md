# Technology Choices

Each choice here was made deliberately. This document explains the "why" so contributors can extend the system with the same reasoning rather than fighting the grain.

---

## Backend: FastAPI

**Why not Django REST Framework or Flask?**

FastAPI was chosen for three reasons that matter specifically to this application:

1. **Native async**: Live session endpoints hold open SSE connections for every audience member simultaneously. Blocking I/O (sync SQLAlchemy, sync Redis) would exhaust the thread pool instantly. FastAPI + asyncio + asyncmy handles hundreds of concurrent open connections on a single thread.

2. **Pydantic validation at the boundary**: Every API request is validated by a Pydantic model before any service logic runs. This removes an entire class of bugs (type errors in service layer) and produces clear error responses without extra code.

3. **Interactive docs for free**: Swagger UI at `/api/docs` is auto-generated from route signatures. This is directly useful for exam participants calling the public endpoints from custom integrations.

---

## Database: MySQL 8

**Why not PostgreSQL?**

The production host is an OCI compute instance with an existing MySQL 8 installation managed via aaPanel. PostgreSQL would have required a second service, additional configuration, and a different operator skill set for maintenance. MySQL 8 covers everything this application needs: JSON columns, window functions, full-text search, and reliable async support via `asyncmy`.

The ORM layer (`SQLAlchemy 2.x async`) abstracts the dialect well enough that migrating later would require only driver and migration changes, not service-layer changes.

---

## Cache and Pub-Sub: Redis

Redis does three distinct jobs here, and each one matters:

| Job | Why Redis |
|---|---|
| **Session pub-sub** | A quiz session can have 200+ audience SSE connections. When the host advances a question, a single `PUBLISH` to the session channel fans out to every subscriber instantly — no polling, no per-connection logic. |
| **JWT blocklist** | On logout, the token's `jti` is added to Redis with a TTL matching the remaining token lifetime. This makes logout immediate without querying MySQL on every request. |
| **Tier cache** | Tier limits are checked on every action. Reading from MySQL on every check would add latency at scale. Redis caches the result for 5 minutes. |
| **OTP storage** | Exam OTPs have a 10-minute TTL. Redis TTL handles expiry automatically — no cron job needed. |
| **OAuth CSRF state** | Google OAuth state tokens stored for 10 minutes; auto-expire via TTL. |

---

## Real-time: Server-Sent Events (not WebSockets)

The live quiz and poll flow is strictly unidirectional: the server pushes state to the audience. Audience members never send data over the real-time channel (answers go via normal POST requests).

SSE advantages over WebSockets for this use case:

- Works through all HTTP/1.1 proxies and load balancers without `Upgrade` header support.
- No protocol negotiation — the browser opens a `GET` to `/events/session/{id}` and starts reading.
- FastAPI's `StreamingResponse` with `text/event-stream` content type is all that's needed; no extra library.
- Polling fallback (`@microsoft/fetch-event-source`) handles the cases where long connections are killed by corporate firewalls or mobile networks switching between cells.

The tradeoff is that truly bidirectional real-time interaction (e.g., collaborative editing) is not possible with SSE alone. This application does not require it.

---

## Frontend: React 18 + Ant Design 5 (ProLayout)

**Why Ant Design ProLayout instead of a custom layout or Tailwind?**

ProLayout (from `@ant-design/pro-components`) ships a production-grade admin shell: collapsible sidebar, header with actions, breadcrumbs, responsive behaviour. Building this from scratch with Tailwind would have cost weeks and introduced ongoing maintenance for layout edge cases.

For the host-facing dashboard (a data-dense admin interface), Ant Design's component density and data grid quality are well-matched. For the participant-facing pages (join, exam, poll session), custom CSS and lightweight components are used instead — ProLayout would be over-engineered for a mobile-first single-action view.

**State management: Redux Toolkit**

Auth state (user profile, role, tenant) needs to be accessible from every page. RTK's `createSlice` is used only for global state; local UI state stays in component hooks. No over-engineered store.

**i18n: react-i18next**

11 languages, all loaded as static JSON files. No server-side translation at runtime. The key constraint: database-stored content (question text, answer options) is never translated — only UI strings are.

---

## Auth: HttpOnly Cookie JWT

**Why cookies instead of localStorage?**

`localStorage` is accessible to any JavaScript on the page. If a third-party script (analytics, chat widget) is compromised (supply-chain attack), it can read and exfiltrate the token. An HttpOnly cookie is inaccessible to JavaScript entirely.

The tradeoff is CSRF risk. This is mitigated by:
- `SameSite=Lax` cookie attribute (blocks cross-site POST in modern browsers).
- CSRF state token for the OAuth flow (stored in Redis, validated on callback).

Bearer header (`Authorization: Bearer <token>`) is also accepted for programmatic API clients (scripts, integrations) that cannot use cookies.

---

## AI: Google Gemini 2.0 Flash

**Why not GPT-4 or Claude?**

Gemini 2.0 Flash has a free tier with sufficient quota for this application's current traffic. The structured output (JSON schema enforcement) is reliable for question generation without prompt engineering for output parsing. The API is integrated via `google-genai` SDK.

**Local fallback: Ollama**

For tenants who need offline or private AI (corporate environments without external API access), Ollama runs locally. It handles distractor generation and question rewriting. Gemini is used for the more demanding tasks (full question generation, result analysis).

---

## Email: SMTP (configurable)

Transactional email (OTP delivery, exam results) is sent via any standard SMTP provider. The configuration (`SMTP_HOST`, `SMTP_USER`, etc.) is intentionally provider-agnostic — the production deployment uses Titan Mail; development uses any local SMTP trap (MailHog, etc.).

---

## Deployment: Nginx + systemd (not Docker in production)

The production server is a single OCI VM managed with aaPanel. Docker adds complexity (networking, volume mounts, image management) that is unnecessary on a single-host deployment. `systemd` service units (`swayame-backend.service`) provide process supervision, auto-restart, and log management via `journald` without Docker overhead.

Docker is used only for the Selenium testing container (`seleniarm/standalone-chromium`) which needs browser isolation.
