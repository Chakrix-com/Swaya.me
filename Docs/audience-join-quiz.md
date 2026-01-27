## Audience Participation – Join Quiz (MVP)

This diagram describes how an audience member joins an active quiz
using a code or link, without requiring authentication.

The flow focuses on validation, session binding, and readiness
for realtime participation.

## Phase 1 — Macro view (big picture)
```mermaid
sequenceDiagram
  autonumber
  actor A as Audience
  participant UI as Audience UI
  participant Backend as Platform (Backend)
  participant Realtime as Results / Export (Realtime)

  A->>UI: Open join link / enter code / QR Code
  UI->>Backend: Join request

  Backend->>Backend: Validate live quiz session
  Backend->>Backend: Prepare audience session

  Backend->>Realtime: Register for live updates
  Realtime-->>UI: Ready / subscribed

  UI-->>A: Waiting for quiz to start
```

## Phase 2 - First-level click-through 
```mermaid
sequenceDiagram
  autonumber
  actor A as Audience
  participant UI as Audience UI
  participant API as API Service
  participant Platform as Platform (Backend)
  participant DB as Database
  participant Session as Live Session
  participant Realtime as Results / Export (Realtime)

  A->>UI: Open join page (link / code / scan QR code)
  UI-->>A: Prompt for join code if required

  A->>UI: Submit join code
  UI->>API: Join request (code)

  API->>Platform: Join intent
  Platform->>Session: Resolve live session
  Session-->>Platform: Live session context

  Platform->>DB: Lookup quiz session
  DB-->>Platform: Session metadata (state, quiz reference)

  alt Session exists and ACTIVE
    Platform->>Platform: Create audience session (in-memory)
    Platform->>Realtime: Register participant for live updates
    Realtime-->>UI: Subscribed to live results
    UI-->>A: Waiting / lobby state
  else Session invalid or ENDED
    Platform-->>UI: Join rejected (invalid / ended)
    UI-->>A: Display error
  end
```

## Phase 3 - Detailed view

```mermaid
sequenceDiagram
  autonumber
  actor A as Audience
  participant UI as Audience UI
  participant API as API Service
  participant Platform as Platform (Backend)
  participant DB as Database
  participant Session as Live Session
  participant Realtime as Results / Export (Realtime)

  %% Entry point
  A->>UI: Open join page

  alt Join via QR Code
    UI->>UI: Decode QR code
    UI->>API: Join request (session identifier)
  else Join via Code
    UI-->>A: Prompt for join code
    A->>UI: Enter join code
    UI->>API: Join request (code)
  end

  %% Backend processing
  API->>Platform: Join intent
  Platform->>Session: Resolve live session
  Session-->>Platform: Live session context

  Platform->>DB: Validate quiz & session existence
  DB-->>Platform: Session metadata (state, quiz reference)

  Platform->>Platform: Check session state == ACTIVE

  alt Session valid and ACTIVE
    Platform->>Platform: Create audience session (anonymous, in-memory)
    Platform->>Realtime: Register participant for live updates
    Realtime-->>UI: Subscription acknowledged
    UI-->>A: Waiting / lobby state
  else Session invalid / ENDED
    Platform-->>UI: Join rejected (reason)
    UI-->>A: Display error and guidance
  end

```
---

## Interpretation of Actors (Codebase Perspective)

This section clarifies how the actors shown in the diagram map to
responsibilities and code locations within the repository.

Actors in this diagram represent **execution and responsibility boundaries**,
not concrete classes, APIs, or infrastructure components.

---

### Audience

**Audience** represents an external participant attempting to join
an active quiz session.

Important clarifications:
- Audience is **not** a code module
- Audience is **not** a tenant
- Audience is an external actor interacting with the platform

From a codebase perspective:
- Audience interactions enter the system via service entry points
- Audience actions are always resolved **within a tenant context**

Relevant areas:

```text
product-code/
├── services/
│   ├── api/          # Join request entry point
│   └── realtime/     # Live updates to audience
└── tenants/
    └── contexts/     # Audience bound to tenant + quiz session
```

Audience identity in MVP is:
- anonymous
- session-scoped
- non-persistent

---

### Platform

**Platform** represents the core runtime kernel responsible for
orchestrating quiz lifecycle and state.

Platform responsibilities in this flow:
- Validate quiz session existence
- Validate quiz session is active
- Create an audience session context
- Coordinate with the realtime layer
- Determine join success or rejection

Platform is intentionally:
- transport-agnostic
- tenant-agnostic at code level
- feature-orchestration focused

Relevant areas:

```text
product-code/
└── platform/
    ├── lifecycle/
    ├── configuration/
    ├── policies/
    └── extension-points/
```

The platform does **not** handle:
- HTTP or WebSocket specifics
- Connection management
- UI concerns

---

### Realtime

**Realtime** represents a dedicated execution boundary for
live message propagation.

It is separated from the platform to:
- isolate scaling behavior
- isolate cost characteristics
- reduce blast radius during failures

Realtime responsibilities in this flow:
- Register audience for live updates
- Broadcast questions and results
- Push updates to connected participants

Relevant areas:

```text
product-code/
├── services/
│   └── realtime/     # Connection and fan-out handling
└── libs/
    └── contracts/
        └── realtime/ # Message contracts and events
```

Realtime is:
- feature-agnostic
- tenant-scoped at runtime
- replaceable without changing platform logic

---

## How the Flow Traverses the Codebase

The diagram conceptually maps to the following execution flow:

1. Audience initiates join via service entry point
2. Platform resolves tenant and quiz session context
3. Platform validates session state
4. Platform creates an audience session context
5. Platform registers audience with realtime layer
6. Realtime pushes live updates to audience

In folder terms:

```text
Audience (external)
        ↓
services/api/
        ↓
platform/
        ↓
tenants/contexts/
        ↓
platform/
        ↓
services/realtime/
        ↓
Audience
```

This separation ensures:
- tenant isolation
- controlled blast radius
- independent scaling of realtime workloads

---

## Architectural Guardrails (MVP)

- Audience logic must not bypass tenant context resolution
- Platform must not manage realtime connections directly
- Realtime must not contain business or quiz logic
- Join flow must remain valid without authentication

These guardrails protect the system from early coupling and
support future evolution to multi-tenant and distributed deployments.

---
