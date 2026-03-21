# User Roles & Personas

## Core Roles

| Role | Definition | Core Responsibility | Authentication | Scope |
|------|------------|---------------------|----------------|-------|
| **Host** | Session owner and quiz creator | Run and control quiz sessions | Email + password (JWT) | Full control over owned quizzes |
| **Audience** | Anonymous participant | Engage in live quiz sessions | None (anonymous) | Session-scoped participation only |

---

## Host Persona

### Identity
- Authenticated user (email + password)
- Owns quiz definitions
- Controls live quiz sessions

### Capabilities (MVP)
- Login to platform
- Create quiz with title
- Add MCQ questions (4 options, 1 correct)
- Start quiz and generate join code
- Advance to next question
- End quiz session
- View live answer aggregation
- View results after quiz ends

### Restrictions (MVP)
- Cannot modify quiz during live session
- Cannot skip backward through questions
- Cannot allow answer changes
- No access to historical analytics (post-MVP)

### Authentication Flow
1. Host opens login page
2. Submits email + password
3. Backend validates credentials
4. JWT token issued
5. Token stored in frontend (localStorage or httpOnly cookie)
6. Token included in all API requests

### JWT Claims (MVP)
```json
{
  "sub": "user_id",
  "email": "host@example.com",
  "role": "host",
  "iat": 1234567890,
  "exp": 1234654290
}
```

---

## Audience Persona

### Identity
- Anonymous participant
- No persistent identity
- Session-bound only

### Capabilities (MVP)
- Join quiz via code or link
- View active question
- Submit one answer per question
- View submission confirmation
- View correct answer after question closes
- View live results

### Restrictions (MVP)
- Cannot change submitted answers
- Cannot view question history
- Cannot access quiz before joining
- Session expires when quiz ends

### Join Flow
1. Audience receives join code/link from host
2. Opens join page
3. Enters code (if not in URL)
4. Platform validates session
5. If valid, audience is registered in-memory
6. Real-time connection established
7. Audience waits for quiz to start

### Session Binding
- Each audience member gets ephemeral session ID
- Session ID tied to quiz session
- No cross-session identity
- Session cleared on quiz end

---

## Future Roles (Post-MVP)

### Moderator / Co-Host
- **Definition**: Content governor with moderation powers
- **Responsibility**: Ensure safe and relevant audience content
- **Capabilities**: Approve/hide questions, highlight content, moderation queue
- **Restrictions**: Cannot create or control quiz sessions

### Admin
- **Definition**: Platform administrator
- **Responsibility**: Manage users, tenants, and system settings
- **Capabilities**: User management, tenant configuration, system monitoring
- **Restrictions**: Not included in MVP scope

---

## Role-Based Access Control (RBAC) — Post-MVP

| Action | Host | Moderator | Audience | Admin |
|--------|------|-----------|----------|-------|
| Create quiz | ✅ | ❌ | ❌ | ✅ |
| Start quiz | ✅ | ❌ | ❌ | ✅ |
| Advance question | ✅ | ❌ | ❌ | ✅ |
| End quiz | ✅ | ❌ | ❌ | ✅ |
| Join quiz | ❌ | ✅ | ✅ | ✅ |
| Submit answer | ❌ | ✅ | ✅ | ✅ |
| View results | ✅ | ✅ | ✅ | ✅ |
| Moderate content | ❌ | ✅ | ❌ | ✅ |
| Manage users | ❌ | ❌ | ❌ | ✅ |

---

## MVP Simplification

For MVP, only **Host** and **Audience** roles are implemented.

**Key Simplifications:**
- No moderator role
- No admin panel
- No multi-user management
- Single host per quiz session
- No role inheritance or delegation
