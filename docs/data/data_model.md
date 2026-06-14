# Data Model

All models use SQLAlchemy ORM. Base class: `persistence/models/base.py`.

## Mixins

### `TimestampMixin` (`persistence/models/base.py`)
| Field | Type | Default |
|---|---|---|
| `created_at` | DateTime | `datetime.utcnow` |
| `updated_at` | DateTime | `datetime.utcnow`; `onupdate=datetime.utcnow` |

### `TenantMixin` (`persistence/models/base.py`)
| Field | Type | Constraints |
|---|---|---|
| `tenant_id` | Integer | FK → `tenants.id`, NOT NULL, indexed |

---

## Core Domain Models (`persistence/models/core.py`)

### `Tenant` (table: `tenants`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK, autoincrement |
| `name` | String(255) | NOT NULL |
| `slug` | String(100) | UNIQUE, NOT NULL, indexed |
| `tier` | Enum(TierEnum) | NOT NULL, default FREE |
| `is_active` | Boolean | NOT NULL, default True |
| `created_at` | DateTime | (TimestampMixin) |
| `updated_at` | DateTime | (TimestampMixin) |

**Relationships**:
- `users` → `User` (one-to-many, back_populates="tenant")
- `events` → `Event` (one-to-many, back_populates="tenant")

**Used in**: `core/auth/service_async.py`, `core/auth/dependencies.py`, `broker/policies/tenant_isolation.py`, all services that enforce tenant isolation

---

### `User` (table: `users`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `tenant_id` | Integer | FK → `tenants.id`, NOT NULL, indexed |
| `email` | String(255) | UNIQUE, NOT NULL, indexed |
| `hashed_password` | String(255) | NULLABLE (null for OAuth users) |
| `full_name` | String(255) | NULLABLE |
| `is_active` | Boolean | NOT NULL, default True |
| `role` | Enum(UserRole) | NOT NULL, default `user` |
| `is_email_verified` | Boolean | NOT NULL, default False, server_default="0" |
| `email_verification_token` | String(255) | NULLABLE |
| `reset_password_token` | String(255) | UNIQUE, NULLABLE |
| `reset_password_expires_at` | DateTime(timezone=True) | NULLABLE |
| `last_login_at` | DateTime(timezone=True) | NULLABLE |
| `login_count` | Integer | NOT NULL, default 0 |
| `user_quota` | Integer | NULLABLE (only for role=admin) |
| `managed_by_admin_id` | Integer | FK → `users.id` ondelete=SET NULL, NULLABLE |
| `oauth_provider` | String(50) | NULLABLE |
| `oauth_provider_id` | String(255) | NULLABLE |
| `language_preference` | String(10) | NOT NULL, default 'en' |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Roles**: `super_admin`, `admin`, `user`, `viewer`

**Relationships**:
- `tenant` → `Tenant` (many-to-one)
- `events` → `Event` (one-to-many)
- `activities` → `UserActivity` (one-to-many, cascade delete-orphan)
- `managed_by_admin` → `User` (self-referential, FK=managed_by_admin_id)

**Used in**: Auth service, user management, all `CurrentUser` dependency usages

---

### `Event` (table: `events`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `tenant_id` | Integer | FK → `tenants.id`, NOT NULL, indexed |
| `creator_id` | Integer | FK → `users.id`, NOT NULL |
| `title` | String(255) | NOT NULL |
| `description` | Text | NULLABLE |
| `join_code` | String(10) | UNIQUE, NULLABLE, indexed |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Note**: `join_code` is used by audience to find live sessions

**Used in**: `session_service_async.py` (join by join_code), `auth/service_async.py` (demo event at registration)

---

### `UserActivity` (table: `user_activities`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `user_id` | Integer | FK → `users.id` ondelete=CASCADE, NOT NULL, indexed |
| `tenant_id` | Integer | FK → `tenants.id` ondelete=CASCADE, NOT NULL, indexed |
| `action` | String(100) | NOT NULL, indexed |
| `resource_type` | String(50) | NULLABLE |
| `resource_id` | Integer | NULLABLE |
| `details` | JSON | NULLABLE |
| `ip_address` | String(50) | NULLABLE |
| `user_agent` | String(500) | NULLABLE |
| `created_at` | DateTime | server_default=CURRENT_TIMESTAMP, indexed |

---

### `TierConfiguration` (table: `tier_configurations`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `tier` | Enum(TierEnum) | UNIQUE, NOT NULL |
| `max_participants` | Integer | NOT NULL |
| `max_questions` | Integer | NOT NULL |
| `max_concurrent_events` | Integer | NOT NULL |
| `features` | Text | NULLABLE (JSON string) |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Used in**: `core/config/tier_service.py`

---

### `LanguageUsageEvent` (table: `language_usage_events`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `user_id` | Integer | FK → `users.id` ondelete=SET NULL, NULLABLE |
| `session_id` | String(100) | NULLABLE, indexed |
| `language` | String(10) | NOT NULL, indexed |
| `previous_language` | String(10) | NULLABLE |
| `event_type` | Enum(`initial`\|`change`) | NOT NULL |
| `created_at` | DateTime | server_default=CURRENT_TIMESTAMP, indexed |
| `user_agent` | Text | NULLABLE |
| `ip_address` | String(45) | NULLABLE |
| `tenant_id` | Integer | FK → `tenants.id` ondelete=SET NULL, NULLABLE |

---

## Quiz Domain Models (`persistence/models/quiz.py`)

### `Quiz` (table: `quizzes`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `tenant_id` | Integer | FK → `tenants.id`, NOT NULL, indexed (TenantMixin) |
| `event_id` | Integer | FK → `events.id`, NOT NULL |
| `folder_id` | Integer | FK → `quiz_folders.id` ondelete=SET NULL, NULLABLE, indexed |
| `title` | String(255) | NOT NULL |
| `description` | Text | NULLABLE |
| `quiz_type` | Enum(QuizType) | NOT NULL, default `quiz` |
| `status` | Enum(QuizStatus) | NOT NULL, default `draft` |
| `is_template` | Boolean | NOT NULL, default False |
| `template_scope` | Enum(TemplateScope) | NOT NULL, default `tenant` |
| `poll_slug` | String(64) | UNIQUE, NULLABLE, indexed |
| `offline_start_at` | DATETIME(fsp=6) | NULLABLE |
| `offline_end_at` | DATETIME(fsp=6) | NULLABLE |
| `offline_results_email` | String(255) | NULLABLE |
| `offline_session_id` | Integer | FK → `quiz_sessions.id`, NULLABLE |
| `exam_slug` | String(64) | UNIQUE, NULLABLE, indexed |
| `exam_start_at` | DATETIME(fsp=6) | NULLABLE |
| `exam_end_at` | DATETIME(fsp=6) | NULLABLE |
| `exam_time_limit_seconds` | Integer | NULLABLE |
| `exam_session_id` | Integer | FK → `quiz_sessions.id`, NULLABLE |
| `exam_results_email` | String(255) | NULLABLE |
| `proctoring_policy` | JSON | NULLABLE |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Quiz types**: `quiz`, `poll`, `offline_poll`, `exam`
**Quiz statuses**: `draft`, `ready`, `archived`

**Relationships**:
- `questions` → `Question` (one-to-many, cascade delete-orphan)
- `sessions` → `QuizSession` (one-to-many, FK=QuizSession.quiz_id)
- `folder` → `QuizFolder` (many-to-one)

---

### `QuizFolder` (table: `quiz_folders`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `tenant_id` | Integer | FK → `tenants.id`, NOT NULL (TenantMixin) |
| `parent_id` | Integer | FK → `quiz_folders.id` ondelete=CASCADE, NULLABLE, indexed |
| `name` | String(255) | NOT NULL |
| `sort_order` | Integer | NOT NULL, default 0 |
| `created_by_id` | Integer | FK → `users.id` ondelete=SET NULL, NULLABLE, indexed |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Unique constraint**: `(tenant_id, parent_id, name)` — no two folders with same name under same parent

**Relationships**:
- `parent` → `QuizFolder` (self-referential)
- `children` → `QuizFolder[]` (cascade delete-orphan)
- `quizzes` → `Quiz[]`

---

### `Question` (table: `questions`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `quiz_id` | Integer | FK → `quizzes.id`, NOT NULL |
| `question_type` | Enum(QuestionType) | NOT NULL, default `mcq` |
| `text` | Text | NOT NULL |
| `order` | Integer | NOT NULL |
| `options` | JSON | NULLABLE (list of 4 strings for MCQ) |
| `correct_answer_index` | Integer | NULLABLE (0-3 for MCQ) |
| `question_image_url` | String(500) | NULLABLE |
| `option_images` | JSON | NULLABLE (`{"A": "path", ...}`) |
| `points` | Integer | NOT NULL, default 1 |
| `max_time_seconds` | Integer | NULLABLE |
| `negative_points` | Integer | NOT NULL, default 0 |
| `is_required` | Boolean | NOT NULL, default False |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Question types**: `mcq`, `word_cloud`, `single_line`, `scale`, `paragraph`, `one_word`

---

### `QuizSession` (table: `quiz_sessions`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `tenant_id` | Integer | FK → `tenants.id`, NOT NULL, indexed (TenantMixin) |
| `quiz_id` | Integer | FK → `quizzes.id`, NOT NULL |
| `status` | Enum(QuizSessionStatus) | NOT NULL, default `created` |
| `current_question_index` | Integer | NOT NULL, default -1 |
| `current_question_status` | Enum(QuestionStatus) | NULLABLE, default `pending` |
| `leaderboard_visible` | Boolean | NOT NULL, default True |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Session statuses**: `created`, `active`, `ended`
**Question statuses**: `pending`, `open`, `closed`

**Relationships**:
- `quiz` → `Quiz`
- `participants` → `Participant[]`
- `answers` → `Answer[]`
- `question_timings` → `SessionQuestionTiming[]` (cascade delete-orphan)

---

### `Participant` (table: `participants`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `session_id` | Integer | FK → `quiz_sessions.id`, NOT NULL |
| `display_name` | String(100) | NULLABLE |
| `session_token` | String(255) | UNIQUE, NOT NULL, indexed |
| `is_active` | Boolean | NOT NULL, default True |
| `completed_at` | DATETIME(fsp=6) | NULLABLE |
| `started_at` | DATETIME(fsp=6) | NULLABLE |
| `last_activity_at` | DATETIME(fsp=6) | NULLABLE |
| `is_abandoned` | Boolean | NOT NULL, default False |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Note**: `is_active=False` when host restarts session; cached in Redis for fast-path lookup

---

### `Answer` (table: `answers`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `session_id` | Integer | FK → `quiz_sessions.id`, NOT NULL |
| `participant_id` | Integer | FK → `participants.id`, NOT NULL |
| `question_id` | Integer | FK → `questions.id`, NOT NULL |
| `selected_option_index` | Integer | NULLABLE (0-3 for MCQ) |
| `text_answer` | Text | NULLABLE (text question types) |
| `is_correct` | Boolean | NULLABLE (null for non-MCQ) |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

**Note**: No DB-level unique constraint on `(participant_id, question_id)` — enforced in `answer_service_async.py`

---

### `SessionQuestionTiming` (table: `session_question_timings`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `session_id` | Integer | FK → `quiz_sessions.id`, NOT NULL, indexed |
| `question_id` | Integer | FK → `questions.id`, NOT NULL |
| `question_index` | Integer | NOT NULL |
| `opened_at` | DATETIME(fsp=6) | NOT NULL |
| `closed_at` | DATETIME(fsp=6) | NULLABLE |

**Note**: Multiple rows per question allowed (host may go back and re-show)

---

### `QuizFeedback` (table: `quiz_feedback`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `tenant_id` | Integer | FK → `tenants.id`, NOT NULL (TenantMixin) |
| `quiz_id` | Integer | FK → `quizzes.id`, NOT NULL, indexed |
| `session_id` | Integer | FK → `quiz_sessions.id`, NULLABLE, indexed |
| `participant_id` | Integer | FK → `participants.id`, NULLABLE, indexed |
| `user_id` | Integer | FK → `users.id`, NULLABLE, indexed |
| `source_type` | String(20) | NOT NULL (`participant` \| `user`) |
| `display_name` | String(100) | NULLABLE |
| `rating` | Integer | NULLABLE |
| `feedback_text` | Text | NOT NULL |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

---

## Statistics Models (`persistence/models/stats.py`)

### `StatsSnapshot` (table: `stats_snapshots`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `captured_at` | DateTime | NOT NULL, indexed |
| `granularity` | Enum(HOURLY\|DAILY) | NOT NULL, indexed |
| `scope` | Enum(PLATFORM\|TENANT) | NOT NULL, indexed |
| `tenant_id` | Integer | FK → `tenants.id` ondelete=CASCADE, NULLABLE |
| `stats_data` | JSON | NOT NULL |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

---

## Proctoring Models (`persistence/models/proctoring.py`)

### `PlatformProctoringRule` (table: `platform_proctoring_rules`)
| Field | Type | Constraints |
|---|---|---|
| `id` | BigInteger | PK, autoincrement |
| `rule_id` | String(64) | UNIQUE, NOT NULL, indexed |
| `display_name` | String(128) | NOT NULL |
| `description` | Text | NULLABLE |
| `applies_to` | JSON | NOT NULL (e.g. `{quiz_types: ["exam"]}`) |
| `tier_minimum` | Enum(free/basic/pro/enterprise) | NOT NULL |
| `config_schema` | JSON | NOT NULL |
| `default_config` | JSON | NOT NULL |
| `severity` | Enum(warn\|lock) | NOT NULL, default `warn` |
| `is_silent` | Boolean | NOT NULL, default False |
| `is_active` | Boolean | NOT NULL, default True |
| `created_at` | DATETIME(fsp=6) | server_default=CURRENT_TIMESTAMP(6) |

**Seeded by**: `features/proctoring/rule_registry.py:seed_platform_rules()`

---

### `TenantProctoringPolicy` (table: `tenant_proctoring_policies`)
| Field | Type | Constraints |
|---|---|---|
| `id` | BigInteger | PK |
| `tenant_id` | Integer | NOT NULL, indexed |
| `rule_id` | String(64) | NOT NULL |
| `enabled_for` | JSON | NOT NULL |
| `config_override` | JSON | NULLABLE |
| `is_enabled` | Boolean | NOT NULL, default True |
| `updated_at` | DATETIME(fsp=6) | NULLABLE |
| `updated_by` | Integer | NULLABLE |

**Note**: No FK constraint on `tenant_id` or `rule_id` — plain integers

---

### `ProctoringSession` (table: `proctoring_sessions`)
| Field | Type | Constraints |
|---|---|---|
| `id` | BigInteger | PK |
| `participant_id` | Integer | NOT NULL, indexed |
| `quiz_id` | Integer | NOT NULL, indexed |
| `tenant_id` | Integer | NOT NULL |
| `active_rule_set` | JSON | NOT NULL |
| `violation_count` | Integer | NOT NULL, default 0 |
| `integrity_score` | Integer | NOT NULL, default 100 |
| `is_locked` | Boolean | NOT NULL, default False |
| `locked_at` | DATETIME(fsp=6) | NULLABLE |
| `lock_reason` | String(100) | NULLABLE |
| `browser_fingerprint` | String(512) | NULLABLE |
| `ip_address` | String(64) | NULLABLE |
| `user_agent` | String(512) | NULLABLE |
| `webcam_required` | Boolean | NOT NULL, default False |
| `webcam_granted` | Boolean | NOT NULL, default False |
| `session_started_at` | DATETIME(fsp=6) | NULLABLE |

**Note**: No FK constraints — plain integers for performance

---

### `ProctoringEvent` (table: `proctoring_events`)
| Field | Type | Constraints |
|---|---|---|
| `id` | BigInteger | PK |
| `quiz_id` | Integer | NOT NULL |
| `tenant_id` | Integer | NOT NULL |
| `participant_id` | Integer | NOT NULL |
| `session_token` | String(255) | NOT NULL, indexed |
| `rule_id` | String(64) | NULLABLE |
| `event_type` | String(64) | NOT NULL |
| `occurred_at` | DATETIME(fsp=6) | server_default=CURRENT_TIMESTAMP(6) |
| `event_metadata` | JSON | NULLABLE (column aliased as `metadata`) |

---

## App Feedback Model (`persistence/models/app_feedback.py`)

### `AppFeedback` (table: `app_feedback`)
| Field | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `page_url` | String(500) | NOT NULL |
| `feedback_text` | Text | NOT NULL |
| `rating` | Integer | NULLABLE (1-5) |
| `source_type` | String(20) | NOT NULL (`anonymous` \| `user`) |
| `user_id` | Integer | NULLABLE, indexed (plain int, no FK) |
| `tenant_id` | Integer | NULLABLE, indexed (plain int, no FK) |
| `display_name` | String(100) | NULLABLE |
| `user_email` | String(255) | NULLABLE |
| `user_agent` | String(500) | NULLABLE |
| `created_at` / `updated_at` | DateTime | (TimestampMixin) |

---

## Redis Key Patterns

| Key Pattern | Content | TTL | Set By |
|---|---|---|---|
| `session:{id}:state` | JSON audience state | NOT DERIVABLE | `SessionServiceAsync._write_audience_state_cache()` |
| `session_token:{token}` | `{participant_id, session_id, is_active}` | NOT DERIVABLE | `SessionServiceAsync.join_session()` |
| `session:{id}:participants:count` | Integer counter | 24h | `TierService.increment_participant_count()` |
| `tier_config:{tier}` | Tier config JSON | 5 min | `TierService.get_tier_config()` |
| `proctor:session:{token}` | `{violation_count, is_locked, ...}` | 24h | `proctoring_service_async.init_session()` |
| `proctor:rules:{quiz_id}:{hash}` | Serialized `ResolvedRuleSet` | 1h | `ProctoringContextResolver.resolve()` |
