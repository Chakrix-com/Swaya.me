# Domain Model (Quiz Feature)

This document defines the core domain entities, relationships, and invariants for the Quiz feature in a **multi-tenant SaaS architecture** with tier-based limits.

---

## Multi-Tenant Foundation

### Tenant

Represents an organization/account in the SaaS platform.

**Properties**:
- `tenant_id` (UUID, primary key)
- `name` (string, required)
- `slug` (string, unique, required) - URL-safe identifier
- `subscription_tier` (enum: FREE, BASIC, PRO, ENTERPRISE)
- `subscription_status` (enum: ACTIVE, TRIAL, SUSPENDED, CANCELLED)
- `subscription_start` (timestamp)
- `subscription_end` (timestamp, nullable)
- `billing_cycle` (enum: MONTHLY, ANNUAL, CUSTOM)
- `created_at` (timestamp)
- `updated_at` (timestamp)

**Relationships**:
- Has many Users
- Has many Quizzes
- Has many Quiz Sessions
- Has one TierConfig (via subscription_tier)
- Has many UsageQuotas

**Invariants**:
- Tenant slug must be globally unique
- Active subscription required for quiz operations
- All domain entities must belong to exactly one tenant

---

### TierConfig

Defines configurable limits and features for a subscription tier.

**Properties**:
- `tier_id` (string, primary key: FREE, BASIC, PRO, ENTERPRISE)
- `name` (string, required)
- `limits` (JSON, required) - quota definitions
- `features` (JSON, required) - feature gates
- `is_active` (boolean, default: true)
- `effective_from` (timestamp)
- `updated_at` (timestamp)

**Example limits JSON**:
```json
{
  "max_participants_per_event": 1000,
  "max_questions_per_quiz": 100,
  "max_concurrent_events": 10,
  "max_team_members": 10,
  "event_history_days": 365,
  "storage_mb": 5000,
  "api_calls_per_hour": 10000,
  "exports_per_day": 50
}
```

**Example features JSON**:
```json
{
  "quiz_types": ["mcq", "poll", "word_cloud"],
  "custom_branding": true,
  "branding_removal": true,
  "moderation_queue": true,
  "data_export": true,
  "api_access": "readonly",
  "sso_enabled": false,
  "profanity_mode": "configurable"
}
```

**Invariants**:
- Tier configs are globally defined (not per-tenant)
- Limits must be positive integers or unlimited (-1)
- Features must be boolean or enum values

---

### UsageQuota

Tracks tenant consumption against tier limits.

**Properties**:
- `quota_id` (UUID, primary key)
- `tenant_id` (UUID, foreign key to Tenant)
- `quota_type` (enum: PARTICIPANTS, QUESTIONS, EVENTS, API_CALLS, STORAGE, EXPORTS)
- `period_start` (timestamp)
- `period_end` (timestamp)
- `limit` (integer)
- `consumed` (integer, default: 0)
- `last_updated` (timestamp)

**Relationships**:
- Belongs to one Tenant

**Invariants**:
- consumed <= limit (enforced at application layer)
- Quotas reset based on period boundaries
- Historical quota records are retained for analytics

---

## Core Entities

### User

Represents a host/admin user within a tenant.

**Properties**:
- `user_id` (UUID, primary key)
- `tenant_id` (UUID, foreign key to Tenant) **[NEW]**
- `email` (string, unique per tenant, required)
- `password_hash` (string, required)
- `display_name` (string, required)
- `role` (enum: OWNER, ADMIN, MEMBER)
- `is_active` (boolean, default: true)
- `created_at` (timestamp)
- `last_login_at` (timestamp, nullable)

**Relationships**:
- Belongs to one Tenant
- Has many Quizzes (as creator)

**Invariants**:
- Email must be unique within tenant (not globally)
- At least one OWNER per tenant
- Inactive users cannot create or manage quizzes

---

### Quiz Definition

A reusable description of a quiz that defines questions and correct answers independent of live play.

**Properties**:
- `quiz_id` (UUID, primary key)
- `tenant_id` (UUID, foreign key to Tenant) **[NEW]**
- `title` (string, required)
- `description` (string, optional)
- `host_id` (UUID, foreign key to User)
- `created_at` (timestamp)
- `updated_at` (timestamp)
- `status` (enum: DRAFT, READY, ARCHIVED)

**Relationships**:
- Belongs to one Tenant
- Has many Questions
- Belongs to one Host (User)

**Invariants**:
- Quiz must have at least one question to transition from DRAFT to READY
- Quiz cannot be modified during live session
- Quiz title is required and non-empty
- Quiz and Host must belong to same tenant
- Question count must not exceed tenant's max_questions_per_quiz limit

---

### Question

A single prompt presented to the audience during a quiz session.

**Properties**:
- `question_id` (UUID, primary key)
- `quiz_id` (UUID, foreign key to Quiz)
- `text` (string, required)
- `order` (integer, required)
- `correct_option_id` (UUID, foreign key to Option)
- `created_at` (timestamp)
- `updated_at` (timestamp)

**Relationships**:
- Belongs to one Quiz
- Has many Options (exactly 4 for MVP)
- Has one correct Option

**Invariants**:
- Question must have exactly 4 options (MVP constraint)
- One and only one option must be marked correct
- Question order must be unique within quiz
- Question text is required and non-empty

---

### Option

A possible answer choice for a question.

**Properties**:
- `option_id` (UUID, primary key)
- `question_id` (UUID, foreign key to Question)
- `text` (string, required)
- `order` (integer, required)
- `created_at` (timestamp)

**Relationships**:
- Belongs to one Question

**Invariants**:
- Option text is required and non-empty
- Option order must be unique within question
- Exactly 4 options per question (MVP)

---

### Quiz Session

A live runtime instance of a quiz being played.

**Properties**:
- `session_id` (UUID, primary key)
- `tenant_id` (UUID, foreign key to Tenant) **[NEW]**
- `quiz_id` (UUID, foreign key to Quiz)
- `host_id` (UUID, foreign key to User)
- `join_code` (string, unique, 6 characters)
- `status` (enum: CREATED, ACTIVE, ENDED)
- `current_question_index` (integer, nullable)
- `started_at` (timestamp, nullable)
- `ended_at` (timestamp, nullable)
- `created_at` (timestamp)

**Relationships**:
- Belongs to one Tenant
- References one Quiz
- Belongs to one Host (User)
- Has many Participants
- Has many Submissions

**Invariants**:
- Join code must be unique and active
- Session can only be started once
- Session cannot transition backward (e.g., ENDED → ACTIVE)
- Current question index must be within valid range
- Only one question active at a time
- Participant count must not exceed tenant's max_participants_per_event limit
- Tenant cannot exceed max_concurrent_events limit

**State Transitions**:
```
CREATED → ACTIVE → ENDED
```

---

### Participant

A session-scoped representation of an audience member.

**Properties**:
- `participant_id` (UUID, primary key)
- `session_id` (UUID, foreign key to Quiz Session)
- `display_name` (string, optional)
- `joined_at` (timestamp)
- `last_seen_at` (timestamp)

**Relationships**:
- Belongs to one Quiz Session
- Has many Submissions

**Invariants**:
- Participant is session-scoped (no cross-session identity)
- Participant is anonymous (no authentication)
- Participant is ephemeral (cleared on session end)

---

### Submission

A participant's answer to a question during a live session.

**Properties**:
- `submission_id` (UUID, primary key)
- `session_id` (UUID, foreign key to Quiz Session)
- `participant_id` (UUID, foreign key to Participant)
- `question_id` (UUID, foreign key to Question)
- `option_id` (UUID, foreign key to Option)
- `submitted_at` (timestamp)

**Relationships**:
- Belongs to one Quiz Session
- Belongs to one Participant
- References one Question
- References one Option

**Invariants**:
- One submission per participant per question
- Submissions cannot be changed after recording
- Submissions only accepted when question state is OPEN
- Late submissions (after close) are rejected

---

### User (Host)

A registered user who creates and manages quizzes.

**Properties**:
- `user_id` (UUID, primary key)
- `email` (string, unique, required)
- `password_hash` (string, required)
- `full_name` (string, optional)
- `created_at` (timestamp)
- `updated_at` (timestamp)

**Relationships**:
- Has many Quiz Definitions
- Has many Quiz Sessions

**Invariants**:
- Email must be unique
- Password must be hashed (never stored plain text)
- Email format must be valid

---

## Entity Relationship Diagram

```mermaid
erDiagram
    Tenant ||--o{ User : "has members"
    Tenant ||--o{ Quiz : "owns"
    Tenant ||--o{ QuizSession : "hosts"
    Tenant ||--o{ UsageQuota : "tracks consumption"
    Tenant }o--|| TierConfig : "subscribes to"
    
    User ||--o{ Quiz : creates
    User ||--o{ QuizSession : hosts
    Quiz ||--o{ Question : contains
    Question ||--o{ Option : has
    Question ||--|| Option : correct_answer
    Quiz ||--o{ QuizSession : instantiates
    QuizSession ||--o{ Participant : includes
    QuizSession ||--o{ Submission : records
    Participant ||--o{ Submission : submits
    Question ||--o{ Submission : receives
    Option ||--o{ Submission : selected

    Tenant {
        uuid tenant_id PK
        string name
        string slug UK
        enum subscription_tier
        enum subscription_status
        timestamp subscription_start
        timestamp subscription_end
        enum billing_cycle
        timestamp created_at
        timestamp updated_at
    }

    TierConfig {
        string tier_id PK
        string name
        json limits
        json features
        boolean is_active
        timestamp effective_from
        timestamp updated_at
    }

    UsageQuota {
        uuid quota_id PK
        uuid tenant_id FK
        enum quota_type
        timestamp period_start
        timestamp period_end
        int limit
        int consumed
        timestamp last_updated
    }

    User {
        uuid user_id PK
        uuid tenant_id FK
        string email
        string password_hash
        string display_name
        enum role
        boolean is_active
        timestamp created_at
        timestamp last_login_at
    }

    Quiz {
        uuid quiz_id PK
        uuid tenant_id FK
        uuid host_id FK
        string title
        string description
        enum status
        timestamp created_at
        timestamp updated_at
    }

    Question {
        uuid question_id PK
        uuid quiz_id FK
        string text
        int order
        uuid correct_option_id FK
        timestamp created_at
        timestamp updated_at
    }

    Option {
        uuid option_id PK
        uuid question_id FK
        string text
        int order
        timestamp created_at
    }

    QuizSession {
        uuid session_id PK
        uuid tenant_id FK
        uuid quiz_id FK
        uuid host_id FK
        string join_code UK
        enum status
        int current_question_index
        timestamp started_at
        timestamp ended_at
        timestamp created_at
    }

    Participant {
        uuid participant_id PK
        uuid session_id FK
        string display_name
        timestamp joined_at
        timestamp last_seen_at
    }

    Submission {
        uuid submission_id PK
        uuid session_id FK
        uuid participant_id FK
        uuid question_id FK
        uuid option_id FK
        timestamp submitted_at
    }
```

---

## Aggregates

### Quiz Aggregate
- **Root**: Quiz Definition
- **Members**: Questions, Options
- **Boundary**: Quiz definition lifecycle
- **Rules**: Quiz cannot be deleted if active sessions exist

### Session Aggregate
- **Root**: Quiz Session
- **Members**: Participants, Submissions
- **Boundary**: Live quiz play
- **Rules**: Session state controls all operations

---

## Domain Events (Post-MVP)

- `QuizCreated`
- `QuizPublished`
- `SessionStarted`
- `QuestionOpened`
- `AnswerSubmitted`
- `QuestionClosed`
- `SessionEnded`

These events enable:
- Analytics aggregation
- Audit logging
- Realtime broadcasting

---

## Business Rules Summary

| Rule Area | Description | Enforcement |
|----------|-------------|-------------|
| Quiz Definition | Must have ≥1 question to be READY | Application layer |
| Question Structure | Exactly 4 options, 1 correct | Application + DB constraint |
| Session State | No backward transitions | Application layer |
| Answer Submission | One per participant per question | DB unique constraint |
| Submission Timing | Only when question OPEN | Application layer |
| Answer Mutability | Cannot change after submission | Application layer |

---

## Data Integrity Constraints

### Database Constraints
- Primary keys: UUID (non-sequential, globally unique)
- Foreign keys: CASCADE on delete for owned entities, RESTRICT for references
- Unique constraints: email, join_code, (participant_id, question_id)
- Not null constraints: All required fields

### Application-Level Validations
- Email format validation
- Join code generation (6-character alphanumeric, case-insensitive)
- Question order validation
- State transition validation
- Answer submission timing validation

---

## Performance Considerations

- **Indexing**: 
  - join_code (frequent lookups)
  - session_id + question_id (submission queries)
  - host_id (quiz ownership queries)
- **Caching**: 
  - Active quiz sessions (Redis)
  - Current question state (Redis)
  - Participant sessions (Redis)
- **Aggregation**: 
  - Answer counts computed on question close
  - Cached for realtime display
