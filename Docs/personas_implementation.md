# Objective
Implement an Industry Persona and Feature Flag architecture to dynamically tailor the Swaya.me platform (features and terminology) for different tenant types without writing conditional persona logic in the UI or business logic.

# Key Files & Context
**Backend:**
- `backend/persistence/models/core.py` (Add PersonaConfiguration model, update Tenant model)
- `backend/core/constants/features.py` (New file: Central feature registry)
- `backend/broker/api/superadmin/` (New routes for CRUD on personas)
- `backend/core/security/dependencies.py` (Add `require_feature` dependency)
- `backend/core/auth/service_async.py` (Update login/user-profile response to include active features and i18n context)
- `backend/broker/api/tenant_management.py` (Add persona assignment endpoint to existing tenant management router)
- `backend/persistence/models/audit.py` (New file **only if** the decision in Section 3 is to create a new table rather than extend `UserActivity`; otherwise modify `backend/persistence/models/core.py`)

**Frontend:**
- `frontend/src/store/` (Add active features and i18n context to auth/user state)
- `frontend/src/components/common/FeatureGate.jsx` (New file: React wrapper component)
- `frontend/src/i18n/` (Define terminology contexts)
- `frontend/src/features/superadmin/` (New GUI matrix for mapping features to personas)

# Implementation Steps

## 1. Database and Models (Backend)
- Create `PersonaConfiguration` table in `core.py` with columns: `id`, `slug`, `display_name`, `description`, `features` (JSON), `is_active`, `created_at`, `updated_at`.
  - **`features` column format:** Store as a flat dict `{"feature_key": true/false, ...}` covering every key in `AVAILABLE_FEATURES`. A key absent from the stored JSON must be treated as `default_enabled` for that feature — not as disabled. This contract means new features added to `AVAILABLE_FEATURES` after seeding are automatically visible to all personas that have not explicitly overridden them. Document this fallback contract explicitly; every future feature registration depends on it.
  - **Drop `i18n_context` as a column.** Derive the i18n context from `slug` directly in code: `persona.slug` is passed as the `context` parameter to `react-i18next`. A separate `i18n_context` column that must always equal `slug` is a redundant synchronization burden with no concrete divergence use case. If a divergence case arises in future (e.g., `slug='edu_k12'` but context `'education'`), add the column then via migration. Do not carry the column speculatively.
  - **Soft delete is the canonical deactivation path.** Remove the hard-delete endpoint from the CRUD API. Use `is_active=False` exclusively. The `ON DELETE SET NULL` FK is a DB-level safety net only (e.g., direct DBA SQL), not an application deletion path. Having both a hard-delete API route and `is_active` creates two divergent paths with different side-effects — Redis cleanup and audit logging only fire reliably if all deletions go through the application layer.
  - **`slug` must have a DB-level UNIQUE constraint.** The NULL fallback query (`WHERE slug = 'default'`) and i18n context resolution both assume slug uniqueness. Without it, two personas with `slug = 'default'` cause the fallback query to return multiple rows, producing undefined behavior. Include `unique=True` on the SQLAlchemy column definition and add a corresponding `UNIQUE` index in the Alembic migration.
- Add `persona_id` (ForeignKey, **nullable**, `index=True`) to the `Tenant` model in `core.py`. The index is mandatory — the reverse-index rebuild query `SELECT id FROM tenants WHERE persona_id = ?` and the bulk seeding UPDATE both run against this column; without an index both are full table scans.
- Add `feature_overrides` (JSON, **nullable**) to the `Tenant` model to allow per-tenant customization without creating new personas.
  - **Canonical default is `NULL`, not `{}`.** Both `NULL` and an empty dict `{}` mean "no overrides applied" and must behave identically in the merge function. Using `{}` as a DB default creates unnecessary storage and makes the "no overrides" state ambiguous. The merge function must explicitly handle both as equivalent.
- Add `features_version` (**BigInteger**, nullable=False, default=0, server_default="0") to the `Tenant` model. At the moment of any persona assignment or `feature_overrides` change, set this column to `int(datetime.utcnow().timestamp() * 1000)` (Unix epoch milliseconds). This value is carried directly in the `X-Features-Version` response header and used by the frontend to detect staleness. **The column must be `BigInteger` (`BIGINT` in MySQL) — a 32-bit `Integer` overflows immediately because current epoch ms ≈ 1.7 trillion, which exceeds the INT max of ~2.1 billion.** Using epoch ms has three advantages: (1) it is monotonically increasing; (2) it is self-describing — operators can read when the last change occurred; (3) it is durable across Redis flushes with no atomic counter needed. **Do not use `Tenant.updated_at` as `features_version`** — `Tenant.updated_at` fires on any tenant mutation (name change, tier upgrade, `is_active` toggle), triggering spurious frontend refreshes.
- Set `ON DELETE SET NULL` on the `Tenant.persona_id` FK so that deleting a persona does not hard-fail — the NULL Persona Policy then catches it via the `default` fallback.
- **Guard against deleting the `default` persona:** Add an application-layer check (and optionally a DB trigger) in the superadmin API that rejects any DELETE or deactivation of the row where `slug = 'default'`. This enforces the NULL Persona Policy at the API boundary.
- **Define `is_active` deactivation behavior explicitly:** When a `PersonaConfiguration` is deactivated, all tenants still assigned to it must immediately fall back to the `default` persona. Invalidate their Redis cache keys at the moment of deactivation, not on next request.
- Generate and apply Alembic migrations.
- **Seed initial personas** as part of the migration (see Data Seeding section below). Do not leave the system in a state where existing tenants have `persona_id = NULL` without a defined fallback.

## 2. Feature Registry & Core Logic (Backend)
- **Resolve conflict with existing `TierConfiguration.features`.** `core.py` already has a `TierConfiguration` model with a `features` column (a JSON string of enabled features per tier). Before implementing `PersonaConfiguration.features`, define the precedence rule: which system wins when both gate the same capability? Recommended: `TierConfiguration` continues to gate hard resource limits (max_participants, max_questions, max_concurrent_events); `PersonaConfiguration` gates UI feature visibility and terminology. These are orthogonal concerns and must not overlap. Document any features that currently live in `TierConfiguration.features` and migrate them explicitly to `AVAILABLE_FEATURES` or leave them in the tier system — never gate the same key in both systems simultaneously.
- Create `backend/core/constants/features.py` exposing `AVAILABLE_FEATURES` as a list of dictionaries. Each entry **must** conform to this schema:
  ```python
  {
      "key": str,           # unique snake_case identifier, e.g. "live_quiz"
      "display_name": str,  # shown in superadmin GUI
      "category": str,      # grouping label — must be a value from PERSONA_CATEGORIES
      "description": str,   # one-sentence explanation for superadmins
      "default_enabled": bool,  # state applied when a new persona is created
      "requires": List[str],    # (Optional) keys of prerequisite features
      "is_paid": bool,          # (Optional) if True, requires subscription validation
      "min_tier": str,          # (Required if is_paid=True) minimum TierEnum value, e.g. "pro"
  }
  ```
- **Also define `AVAILABLE_FEATURES_MAP`** in the same module as `AVAILABLE_FEATURES_MAP: dict[str, dict] = {f["key"]: f for f in AVAILABLE_FEATURES}`. Every lookup by key (override validation, `require_feature`, `FEATURE_DEPENDENCY_CLOSURE` construction) must use this dict for O(1) access. The list form (`AVAILABLE_FEATURES`) is retained for GUI ordering; all programmatic access uses the map. Implementing key lookups against the list (e.g., `next(f for f in AVAILABLE_FEATURES if f["key"] == key)`) is O(n) and must not appear in the codebase.
- **`is_paid` validation must integrate with the existing `TierService`.** There is no `Subscription` model in the codebase. When `is_paid=True`, `require_feature` must call `TierService.get_tier_config()` and validate the tenant's `TierEnum` against the feature's `min_tier` threshold. Do not reference an undefined subscription model.
- **Key Deprecation Strategy:** Define a `DEPRECATED_FEATURES` list in `features.py`. Keys in this list are ignored by `require_feature` and should be pruned from DB JSON columns via a periodic migration utility to prevent "Ghost Key" accumulation. Keys in `DEPRECATED_FEATURES` must not appear in any other feature's `requires` field — validate this at startup as part of cycle detection.
- **Feature Key Rename Policy:** Renaming a feature key in `AVAILABLE_FEATURES` is a breaking change. The absent-key-equals-`default_enabled` fallback means the old key silently persists as a ghost in all `PersonaConfiguration.features` and `Tenant.feature_overrides` JSON blobs. A rename must be implemented as: (1) add new key to `AVAILABLE_FEATURES`; (2) add old key to `DEPRECATED_FEATURES`; (3) write a migration utility that rewrites the old key to the new key in all JSON blobs. The CLI tool must include a `rename-feature` subcommand that executes all three steps atomically.
- **Pre-compute the transitive `requires` closure at module load.** Since `AVAILABLE_FEATURES` and its `requires` graph are module-level constants, the full dependency closure for every feature key is known at import time. Build a `FEATURE_DEPENDENCY_CLOSURE: dict[str, set[str]]` at module level (e.g., `{"A": {"B", "C"}, "B": {"C"}, ...}`). This turns `require_feature` transitive resolution from an O(depth) traversal into an O(1) dict lookup, eliminates all runtime cycle risk, and makes the dependency graph inspectable.
  - **Cycle detection raises `RuntimeError` at module import.** If a cycle is detected while building `FEATURE_DEPENDENCY_CLOSURE`, raise `RuntimeError("Circular dependency in AVAILABLE_FEATURES requires graph: <cycle path>")` at module level. This propagates as an `ImportError` and prevents `features.py` from being imported, which prevents FastAPI from starting. The error message must include the cycle path (e.g., `"A → B → A"`) so operators can identify and fix it from startup logs without needing a debugger.
  - Startup validation must also assert that: (a) all keys referenced in `requires` fields exist in `AVAILABLE_FEATURES_MAP`; (b) no key in `DEPRECATED_FEATURES` appears in any `requires` field. Both of these also raise `RuntimeError` at module load.
- **`MINIMUM_VIABLE_FEATURES` as a module-level constant.** Derive it at module load as `[f for f in AVAILABLE_FEATURES if f["default_enabled"] and not f.get("requires")]`. No startup hook or lazy initialization is needed — `AVAILABLE_FEATURES` is already available at import time.
- **Entitlement Layer vs. Feature Layer:** Distinguish between what a persona *can* do and what a tenant has *paid* for. If `is_paid=True`, `require_feature` should also validate the tenant's subscription status via `TierService`. If a feature is enabled in a persona but unpaid, the system should trigger "Marketing Mode" (upsell).
- **Define `PERSONA_CATEGORIES` as an explicit enum or constant** in `backend/core/constants/features.py`. The `category` field in `AVAILABLE_FEATURES` must use values from this set only. Free-text categories entered by different developers will fragment the GUI matrix into inconsistent groupings.
- Create a dependency `require_feature(feature_key: str)` in `backend/core/security/dependencies.py`. It must be implemented as a **FastAPI dependency factory** — a function that returns an inner async dependency — so that FastAPI can inject `get_async_db` (never `get_db`) and `get_current_user`:
  ```python
  def require_feature(feature_key: str):
      async def dependency(
          current_user=Depends(get_current_user),
          db: AsyncSession = Depends(get_async_db),
          request: Request = None,
      ):
          ...
      return Depends(dependency)
  ```
  Using `get_db` (the sync session, Alembic-only) here is a known footgun — CLAUDE.md §2 explicitly prohibits importing it in any new route or service. The factory pattern must declare `get_async_db` explicitly.
  - Derive the tenant's active feature list by merging its persona's features with any `feature_overrides` defined at the tenant level.
  - **Cache the result in Redis** under `persona:features:{tenant_id}` with a 5-minute TTL.
  - **Specify the cached format:** Store the merged result as a JSON dict `{"feature_key": true/false, ...}` covering all keys in `AVAILABLE_FEATURES`. The writer (invalidation and repopulation) and reader (`require_feature`) must agree on this format explicitly. Leaving it implicit causes deserialization errors when implemented by different developers.
  - **Invalidate the cache** whenever a `PersonaConfiguration` OR a `Tenant` (if overrides change) is saved.
  - **Bulk invalidation on persona change:** A single `PersonaConfiguration` is shared across many tenants. Maintain a reverse-index Redis set `persona:tenants:{persona_id}` (add to it on tenant save, remove on reassignment). When a persona is updated, iterate this set and invalidate `persona:features:{tenant_id}` for every member atomically. Without this, tenants will serve stale features for up to 5 minutes after any persona-level change.
  - **`persona:tenants:{persona_id}` Redis set must have a TTL.** Per the project's Redis Key Hygiene rule (CLAUDE.md §4): no unbounded keys. Set a TTL of at least 24 hours with a rebuild-on-miss strategy (see below). This makes the set a long-lived cache rather than a permanent structure, consistent with the rule.
  - **Reverse-index rebuild strategy:** The `persona:tenants:{persona_id}` set is a Redis-only structure with no DB backing. If Redis is flushed (a known operational risk per CLAUDE.md — "Tier counters after Redis flush"), the reverse-index is lost. On a cache miss or on startup, rebuild this set from a DB query: `SELECT id FROM tenants WHERE persona_id = ?`. Do not treat the Redis set as the source of truth; treat it as a cache of the DB FK relationship.
  - **Cold-start DB stampede mitigation.** On Redis flush, every incoming request for every tenant will miss cache simultaneously, and all reverse-index rebuild queries will fire concurrently. Add a startup background task (registered in APScheduler) that pre-populates `persona:features:{tenant_id}` for all active tenants in batches of 100 before the first request is served. This converts the thundering herd into a controlled warm-up.
  - **Persona reassignment reverse-index update must be atomic.** When a tenant is reassigned from persona A to persona B, two Redis operations are needed: remove `tenant_id` from `persona:tenants:{A_id}` and add it to `persona:tenants:{B_id}`. A process crash between these two commands leaves the reverse-index permanently inconsistent. Wrap both in a Redis `MULTI`/`EXEC` transaction or a Lua script. Prefer a Lua script — `MULTI`/`EXEC` does not work correctly across key slots in Redis Cluster, whereas a Lua script does.
  - **Transitive `requires` resolution:** Use the pre-computed `FEATURE_DEPENDENCY_CLOSURE` dict — an O(1) lookup, not a runtime graph traversal. If feature A's closure includes B and C, confirm all are enabled before granting access.
  - **Conflict Resolution Policy (Fail Closed):** If any link in the `requires` chain is `false` (whether due to Persona settings, an Override, or an Entitlement failure), the top-level feature must remain disabled. Overrides cannot "force-enable" a feature whose prerequisites are missing.
  - **Performance Baselines:** Maintain a strict latency budget for `require_feature` checks.
    - **Target:** < 5ms on Redis cache hit; < 20ms on cache miss/DB fallback.
    - **Monitoring:** Log any resolution taking > 50ms as a "Slow Feature Check" for investigation.
  - **In-request caching of the resolved feature set:** If a single request triggers multiple `require_feature` checks for the same tenant (e.g., a dashboard route behind several feature flags), each check currently makes a Redis round-trip. Cache the resolved feature dict in `request.state` on the first call; subsequent `require_feature` calls within the same request read from `request.state` instead. This reduces N Redis round-trips to 1 per request.
  - If `persona_id IS NULL`, apply the default persona's feature set.
  - **`require_feature` 403 response body must be distinguishable from role-based 403s.** Return `{"detail": "feature_disabled", "feature": "<key>"}` on feature-gated denial, versus `{"detail": "Insufficient permissions"}` for role-based denial. The frontend must route these to different UX flows (upsell modal vs. access denied message). Define this contract in the schema and assert it in tests.
- **Validate `feature_overrides` at the API layer:** Before saving a tenant's `feature_overrides`, validate that every key in the JSON exists in `AVAILABLE_FEATURES_MAP`. Unknown keys must be rejected with a 422, not silently ignored. Silent acceptance creates invisible misconfiguration.
- **Define `feature_overrides` merge semantics explicitly:** Overrides must be able to both *enable* and *disable* features relative to the persona's value. The resolved value for a feature key is: `feature_overrides[key]` if present, else `persona.features[key]` if present, else `AVAILABLE_FEATURES_MAP[key]["default_enabled"]`. This order must be documented and unit-tested.
- **`super_admin` role is exempt from `require_feature` checks unconditionally.** Add this bypass at the top of the `require_feature` dependency, before any Redis or DB lookup. This prevents super_admins from being locked out of platform management if tenant_id=1's persona is misconfigured. Document this exemption clearly — it is a privileged bypass, not a bug.
- **Redis-down fallback in `require_feature`:** If the Redis read raises a connection error (post-startup Redis failure), do not propagate a 500. Fall back to a direct DB lookup for the tenant's persona and compute the merged feature set from the DB. Log the Redis failure as an error. An unhandled Redis connection error in `require_feature` will return HTTP 500 on every feature-gated route for the duration of the outage.
- **`DISABLE_FEATURE_GATING` emergency kill switch:** Implement an environment variable `DISABLE_FEATURE_GATING=true` that causes `require_feature` to always return `True`. This check must be the very first line of `require_feature`, before any role bypass, Redis lookup, or DB query. When this variable is set, log a `WARNING` at application startup ("Feature gating disabled — all features enabled for all tenants. Set DISABLE_FEATURE_GATING=false to re-enable.") so that operators who forget to unset it after an incident are alerted on the next restart.
- **`features_version` increment on `AVAILABLE_FEATURES` registry change.** When a code deploy adds or removes features from `AVAILABLE_FEATURES`, clients with a cached `/me` response won't see the change until their `features_version` changes. The startup lifespan must: (1) compute a hash of the sorted feature keys (e.g., `hashlib.md5(sorted(AVAILABLE_FEATURES_MAP.keys()).encode()).hexdigest()`); (2) compare it to a Redis key `features_registry_hash`; (3) if changed, bulk-set `features_version = NOW_MS` for all active tenants and update `features_registry_hash`. This forces all clients to refresh `/me` after any registry change without requiring a separate trigger.
- Modify the login/user-profile API (`backend/core/auth/service_async.py`) to return `active_features` (array of strings) and `i18n_context` (derived from `persona.slug`).

## 3. Superadmin API & GUI
- **Backend API:** CRUD endpoints for `PersonaConfiguration`. **Audit logging is mandatory** for all changes to personas or tenant-level overrides.
- **Audit Log Infrastructure: extend `UserActivity` or create a new table — decide before writing any logging code.**
  - `core.py` already contains a `UserActivity` table (`id`, `user_id`, `tenant_id`, `action`, `resource_type`, `resource_id`, `details`, `ip_address`, `created_at`). Evaluate whether `UserActivity` can be extended with `before_state` (JSON), `after_state` (JSON), and `target_tenant_id` (Integer, nullable) to cover persona audit needs. Extending the existing table avoids a second audit infrastructure and is preferred unless there is a concrete reason for separation (e.g., different retention, different access control, or volume concerns). If a new `audit_log` table is created instead, document the explicit reason and update the Key Files section accordingly — do not leave two parallel audit systems without a clear ownership boundary.
  - **`actor_id` vs `user_id` naming:** The target schema uses `actor_id`, but the existing `UserActivity` model uses `user_id` as the FK to `users`. If extending `UserActivity`, decide before writing the migration whether to rename `user_id` → `actor_id` (a breaking change requiring all existing queries to be updated) or to keep `user_id` and alias it as `actor_id` in the application layer. If creating a new table, `actor_id` is unambiguous. Do not mix both column names in the same codebase.
  - Whichever table is used: schema must include `id`, `actor_id` (or `user_id`), `target_tenant_id`, `action`, `entity_type`, `entity_id`, `before_state` JSON, `after_state` JSON, `timestamp`.
  - **Retention Policy:** Define a 1-year retention policy for the audit log. Add a background pruning task registered with APScheduler in `main.py` (following the existing scheduler pattern — see `start_scheduler()` in CLAUDE.md §1) to delete entries older than 12 months monthly. **If extending `UserActivity`, scope the pruning DELETE to persona/override actions only** (e.g., `WHERE action IN ('persona_assign', 'feature_override_change', ...) AND created_at < NOW() - INTERVAL 1 YEAR`). An unscoped delete would also purge login events and other activity records that may have different retention requirements.
  - **`target_tenant_id` is required.** When a `super_admin` (tenant_id=1) modifies another tenant's persona or overrides, `actor_id` alone is not enough to answer "show me all changes made to Tenant X's configuration." The `target_tenant_id` field records whose data was affected, independently of who acted.
  - **Index `target_tenant_id`, `actor_id`, and `timestamp` in the migration.** Compliance queries ("all changes to Tenant X," "all changes by actor Y in date range Z") will be full table scans without these indexes. Include explicit `CREATE INDEX` statements in the Alembic migration alongside the table creation.
- **Permission boundary — resolved decisions:**

  | Action | `super_admin` | `admin` | `user` | `viewer` |
  |---|---|---|---|---|
  | Create / delete a `PersonaConfiguration` | Yes | No | No | No |
  | Assign a persona to a tenant | Yes | No | No | No |
  | Read their own tenant's active features | Yes | Yes | Yes | Yes |
  | Write `feature_overrides` for their own tenant | Yes | **No (v1)** | No | No |

  **`admin` write access to `feature_overrides` is explicitly disabled in v1.** All override management is `super_admin` only. When v2 enables tenant-level override management, a separate `/admin/feature-overrides` endpoint with scoped permission checks is required; until then, no such endpoint exists and the "Tenant Override" GUI section is hidden from `admin` users. The `viewer` role follows the same read rules as `user` — it can see `active_features` from `/me` but cannot write anything.

- **Persona assignment endpoint lives in `tenant_management.py`.** The `PATCH` endpoint to set `persona_id` on a tenant is a tenant mutation and belongs in the existing `backend/broker/api/tenant_management.py`, not in a new superadmin router. This endpoint requires `Depends(require_super_admin)` and must: set `persona_id`, update `features_version` to `NOW_MS`, invalidate the tenant's Redis cache, and update the `persona:tenants:*` reverse-index atomically.

- **Add `GET /superadmin/features` endpoint** that serialises `AVAILABLE_FEATURES` (key, display_name, category, description, default_enabled, requires, is_paid, min_tier) as JSON. The superadmin GUI cannot render the feature matrix dynamically without this endpoint — it cannot import a Python constant directly. This endpoint must be read-only and protected by `require_super_admin`.
  - **Cache this response at both layers.** Add server-side Redis caching keyed at `superadmin:features_registry` — write a fresh value on every startup (not just cache miss) so that deploys automatically invalidate stale cached registry data. Also add `Cache-Control: public, max-age=3600` as a browser cache hint. Without server-side caching, the persona management GUI re-fetches the full feature registry on every page load regardless of the browser cache header.
- **New tenant creation must assign the `default` persona atomically.** The tenant creation endpoint must set `persona_id` to the `default` persona's ID, set `features_version` to `NOW_MS`, and add the new `tenant_id` to the `persona:tenants:{default_id}` Redis set in the same operation.
- **Define new persona `features` initialization.** When a super_admin creates a new persona via the API or GUI, the initial value of the `features` JSON must be specified. Recommended: auto-populate from `AVAILABLE_FEATURES` using each entry's `default_enabled` value, giving the admin a fully-populated starting state to adjust. Requiring the admin to configure every key from scratch is error-prone for registries with many features.
- **Add `POST /superadmin/personas/{id}/clone` endpoint.** The primary super_admin workflow will be "clone an existing persona and adjust a few flags," not building a full feature matrix from scratch. Without a clone endpoint, every new persona requires manually replicating the full configuration — a source of errors at 20+ features. The clone creates a copy with a new `slug` and `display_name` (both are required inputs — return 422 if either is missing); all other `features` fields are identical to the source. **The clone must always default to `is_active=False` regardless of the source's state.** Inheriting `is_active=True` from the source would immediately expose an unreviewed persona to tenants. The super_admin must explicitly activate the clone after review.
- **Add `GET /superadmin/personas/{id}/tenants` endpoint.** Required for basic operational visibility: "which tenants are using this persona?" and "how many tenants have feature X enabled?" Without it, there is no way to assess the blast radius of a persona change before applying it. **This endpoint must support pagination** (cursor-based or offset+limit) — a persona shared by thousands of tenants would produce an unbounded response without it.
- **DX Automation (Feature-Flag CLI tool):** To reduce friction, provide a CLI utility that:
  - Scaffolds a new feature entry in `features.py`.
  - Generates i18n key stubs in all 11 locale files automatically.
  - Audits the codebase for "Dead Flags" (keys defined in the registry but not used in code).
  - Validates the `requires` graph for missing keys or cycles before commit.
  - Provides a `rename-feature <old_key> <new_key>` subcommand that atomically: adds the new key to `AVAILABLE_FEATURES`, adds the old key to `DEPRECATED_FEATURES`, and generates a migration to rewrite old key references in all `PersonaConfiguration.features` and `Tenant.feature_overrides` JSON blobs.
- **Frontend GUI:** Build a "Persona Management" screen.
  - Group features by `category` in a matrix.
  - **Dependency Enforcement:** UI should visually indicate and auto-select prerequisite features defined in the `requires` field.
  - **Block saving an invalid persona state.** The GUI must prevent saving a configuration where a feature is enabled but a feature in its `requires` chain is disabled. Auto-select is a convenience hint; the save guard is correctness enforcement. A super_admin who dismisses the auto-select hint and saves anyway must receive an error, not a silent invalid configuration.
  - Include a "Tenant Override" interface to manage specific feature toggles for power users (super_admin only in v1).
  - **Effective Permissions Debugger:** Add a "Simulate/Trace" view that shows the final resolved feature set for a specific tenant, highlighting whether a feature is enabled/disabled due to the Persona, an Override, or a Prerequisite failure.

## 4. Frontend Feature Guarding & State
- **State:** Update Redux/Context. Re-fetch from `/me` on page load.
  - **Client-side caching for `/me`:** Do not re-fetch on every navigation event unconditionally. Cache the `active_features` response in Redux with a timestamp and treat it as fresh for a configurable TTL (e.g., 5 minutes, defined as a named constant — not a magic number). Re-fetch only if stale or after a 403.
  - **JWT / active_features staleness:** If the client persists `active_features` in Redux Persist or localStorage, a user who stays logged in during a persona change will see the old feature set until `/me` is next called. Add a server-issued `features_version` value to the `/me` response body and to the `X-Features-Version` response header on all API responses. If the stored version differs from the one in any incoming header, trigger an immediate background `/me` refresh before the user hits a 403.
  - **`features_version` must NOT be encoded in the JWT.** CLAUDE.md explicitly warns that adding or renaming a JWT claim forces all existing tokens to be invalid (all users must re-login). `features_version` changes on every persona update — putting it in the JWT would invalidate all sessions on every persona save. Keep it exclusively in the `/me` response body and the `X-Features-Version` response header.
  - **`features_version` source is `Tenant.features_version`.** This is a dedicated `BigInteger` column set to Unix epoch milliseconds on every persona or override change (see Section 1). The frontend treats a higher value as "newer" and triggers a background `/me` refresh. If no stored version exists (first page load before `/me` completes), treat any incoming version as current — do not fire a spurious refresh.
- **Local Development "Override" Mode:** To improve DX, allow the frontend to bypass DB checks in the `development` environment via a `?feature_override=key:true,other_key:false` URL parameter or a LocalStorage entry. This takes precedence over `active_features` from `/me` for testing purposes only. **The guard must be `import.meta.env.MODE === 'development'` — a Vite build-time check, not a runtime flag.** Do not use a `VITE_ENABLE_OVERRIDES` env var that could be accidentally set in `.env.production`. The development override code path must be entirely tree-shaken out of the production bundle.
- **Component:** `<FeatureGate requiredFeature="key" mode="hide|disable|upsell"> {children} </FeatureGate>`.
  - **Gated Feature Discovery:**
    - `hide` (default): Children are not rendered.
    - `disable`: Children are rendered but wrapped in a "disabled" state (e.g., greyed out with a lock icon).
    - `upsell`: Children are rendered but clicks are intercepted to show a "Contact Sales" or "Upgrade" modal.
  - **Define `<FeatureGate>` behavior for an unknown feature key.** If `requiredFeature="typo_key"` is passed and the key is absent from `active_features`, the component must fail closed (hide content) and emit a `console.warn`. Additionally, in development mode, throw a visible error boundary so the unknown key is immediately surfaced to the developer — a silent console warning in production is invisible and the bug will not be caught.
  - **Define `<FeatureGate>` behavior during a background `/me` refresh.** While `active_features` is being updated, the component must render based on the last known state (optimistic) and not flicker to empty. Document this contract so all gate implementations behave consistently.
- **Interceptors:** The global Axios/Fetch interceptor has two distinct responsibilities — both must be implemented:
  1. **On every response:** Read the `X-Features-Version` header and compare it to the version stored in Redux. If the server version is newer, trigger a background `/me` refresh to update `active_features` before the user encounters a gated component.
  2. **On 403 from `require_feature`:** Read the response body. If `detail === "feature_disabled"`, show an upsell/discovery modal. If `detail === "Insufficient permissions"`, show an access-denied message. Do not treat all 403s identically.
- **`X-Features-Version` header requires a FastAPI middleware with a per-request lookup cost.** Adding this header to every authenticated response requires middleware that reads the tenant's current `features_version` from `Tenant.features_version` (via DB or Redis). **This middleware must skip unauthenticated requests entirely** — for routes like `POST /auth/login`, `GET /health`, and public quiz join endpoints there is no `tenant_id` to look up; attempting the lookup will raise a `KeyError` or `AttributeError`. The middleware must check for an authenticated user (JWT present and valid) before any DB/Redis access. Confirm the result is cached in `request.state` to avoid a second round-trip alongside any `require_feature` lookup in the same request.
- **i18n Strategy:** Use `react-i18next` with context. The context key is the persona's `slug` (no separate `i18n_context` column — see Section 1).
  - **Fallback Hierarchy:** If `t('key', { context: 'corporate' })` is missing, fall back to the `default` persona context, then the generic key.
  - **i18n Chunking & Lazy Loading:** To prevent massive translation files, implement chunking based on persona context. The frontend should only load the active persona's terminology context (e.g., `education.json`) rather than downloading all industry variants. The active persona slug is available from the `/me` response; the i18n chunk load must be deferred until `/me` completes. During this window, display a loading spinner only for components that require persona-specific terminology — general navigation, page titles, and non-persona copy should render immediately using the base locale file and must not be blocked by persona chunk loading.
  - **CI smoke test for i18n completeness:** Add a CI step (can be a Jest test or a standalone script) that iterates every entry in `AVAILABLE_FEATURES` and asserts that a translation key exists for it in all 11 locale files (`en, hi, ta, te, ka, bn, gu, es, fr, de, ru`) for every persona context in use. Without this gate, persona-specific copy silently falls back to defaults and the gap is only caught during manual QA.

# Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **QA Combinatorial Explosion** | Define "Standard Profiles" for testing. Use automated sanity checks that iterate through each persona's expected feature set. |
| **"Zombie" UI Components** | Implement global 403 interceptors to catch permission changes and trigger background state refreshes. |
| **i18n Fragmentation** | Strict fallback hierarchy in the i18n helper. Migrate entire feature modules at once to avoid mixed-persona terminology on a single page. |
| **Corrupt Default Persona** | The `MINIMUM_VIABLE_FEATURES` derived-at-module-load fallback ensures basic login and management functionality always works. |
| **Audit/Compliance** | Mandatory audit logs for all Persona and Tenant-level feature changes to track permission shifts. |
| **Stale `active_features` in client** | Include `features_version` (Unix epoch ms from `Tenant.features_version`) in `/me` response. API responses carry this in `X-Features-Version` header; client triggers a background `/me` refresh if the stored version is older. |
| **Bulk cache invalidation miss** | Maintain a Redis reverse-index `persona:tenants:{persona_id}`. On persona save, fan-out cache invalidation to all member tenant IDs atomically. |
| **`requires` bypass at API layer** | `require_feature` uses pre-computed `FEATURE_DEPENDENCY_CLOSURE` dict — full transitive closure resolved at O(1). UI-only enforcement is insufficient. |
| **`feature_overrides` silent misconfiguration** | Validate override keys against `AVAILABLE_FEATURES_MAP` at the API layer. Reject unknown keys with HTTP 422. |
| **`default` persona deletion** | Application-layer guard (and optional DB trigger) blocks DELETE or deactivation of `slug='default'`. |
| **`is_active=False` leaves tenants in undefined state** | Deactivating a persona must immediately invalidate Redis cache for all assigned tenants and cause them to fall back to `default`. |
| **`MINIMUM_VIABLE_FEATURES` drift** | Derive as a module-level constant: `[f for f in AVAILABLE_FEATURES if f["default_enabled"] and not f.get("requires")]`. No deferred hook needed. |
| **Seed migration table lock** | The bulk UPDATE assigning `persona_id` to existing tenants must be looped (e.g., `WHERE persona_id IS NULL LIMIT 500` repeated until affected rows = 0) to avoid a prolonged write lock on the tenants table during migration. |
| **Rollback order gap** | Routes decorated with `Depends(require_feature)` will 500 (not 403) if the migration is reverted while decorators remain. Step 1 of rollback must be: remove all `require_feature` decorators and redeploy; only then run the down-migration. |
| **No point-in-time audit trail** | For compliance in education/proctoring contexts, snapshot the tenant's resolved feature set into the audit log at the time of each persona or override change, not just the delta. |
| **Undefined `PERSONA_CATEGORIES`** | Define `PERSONA_CATEGORIES` as a constant or enum. All `category` values in `AVAILABLE_FEATURES` must come from this set to keep the GUI matrix consistent. |
| **`features` JSON format ambiguity** | Canonical format is `{"feature_key": true/false}`. Absent key = `default_enabled`. Document this contract in code comments at the column definition. |
| **`feature_overrides` merge direction undefined** | Resolved value = `overrides[key]` if present, else `persona.features[key]` if present, else `default_enabled`. Overrides can both enable and disable. Define and unit-test this merge order explicitly. |
| **Circular `requires` → infinite loop** | `FEATURE_DEPENDENCY_CLOSURE` is pre-computed at module load. If a cycle is detected, `RuntimeError` is raised at import time, aborting startup. No runtime traversal ever occurs. |
| **New feature key absent from existing personas** | Absence of a key in `persona.features` resolves to `default_enabled`, not disabled. Codify this as a named function in `require_feature` so the behavior is testable and reviewable. |
| **`super_admin` self-lockout via `require_feature`** | `require_feature` must short-circuit unconditionally for `role == super_admin` before any Redis or DB check. |
| **Redis down post-startup → 500 on gated routes** | `require_feature` must catch Redis connection errors and fall back to a direct DB lookup. Log the failure; do not propagate a 500. |
| **`AVAILABLE_FEATURES` not accessible to frontend** | Add `GET /superadmin/features` endpoint (read-only, `require_super_admin`) serialising `AVAILABLE_FEATURES` as JSON. GUI cannot render the feature matrix without it. |
| **`persona:tenants` reverse-index lost on Redis flush** | On cache miss or startup, rebuild the index from DB: `SELECT id FROM tenants WHERE persona_id = ?`. Redis set is a cache, not source of truth. |
| **`persona:tenants:*` Redis keys have no TTL** | Set a 24-hour TTL on each `persona:tenants:{persona_id}` set with rebuild-on-miss. This complies with the project's Redis Key Hygiene rule (CLAUDE.md §4: no unbounded keys). |
| **New tenants created without explicit persona assignment** | Tenant creation endpoint must set `persona_id = default_id`, set `features_version = NOW_MS`, and add to `persona:tenants:{default_id}` atomically. |
| **`audit_log` table missing `target_tenant_id`** | Add `target_tenant_id` column to the audit log schema so changes made by a super_admin to another tenant's config are queryable by affected tenant. |
| **`features_version` in JWT invalidates all sessions on persona change** | `features_version` must live only in `Tenant.features_version` DB column, `/me` response body, and `X-Features-Version` response header. Never encode in the JWT. |
| **Soft vs hard delete creates divergent paths** | Remove the hard-delete API endpoint. Use `is_active=False` exclusively. `ON DELETE SET NULL` is a DB-level safety net only. |
| **`i18n_context` as separate column** | Column dropped. Derive i18n context from `persona.slug` in code. No synchronization burden. |
| **`features_version` storage mechanism** | Use dedicated `Tenant.features_version` `BigInteger` column set to Unix epoch milliseconds on persona/override change. Self-describing, durable, no spurious fires on unrelated mutations. |
| **`X-Features-Version` middleware adds per-request overhead** | Read `Tenant.features_version` from DB. Cache result in `request.state`. Middleware must skip unauthenticated requests entirely (no JWT = no tenant_id lookup). |
| **Persona reassignment reverse-index not atomic** | Wrap SREM + SADD for `persona:tenants:*` in a Lua script (preferred over `MULTI`/`EXEC` — Lua scripts are cluster-safe). |
| **`admin` override permission decision** | Resolved: tenant `admin`s cannot write `feature_overrides` in v1. All override management is `super_admin` only. No `/admin/feature-overrides` endpoint in v1. |
| **`default` persona "most permissive" is unenforced** | Add save-endpoint validation rejecting `default` persona configs that disable any `default_enabled=True` feature. Or document as convention with audit log + permission boundary as the only safeguard. |
| **New persona `features` initialization undefined** | Auto-populate from `AVAILABLE_FEATURES` `default_enabled` values at creation time. Specify in the persona creation API contract. |
| **No persona clone endpoint** | Add `POST /superadmin/personas/{id}/clone`. Clone always defaults to `is_active=False` regardless of source state — prevents accidental immediate exposure of an unreviewed persona. |
| **No persona tenants observability endpoint** | Add `GET /superadmin/personas/{id}/tenants` with pagination. Required to assess blast radius before changing a persona. |
| **GUI does not block saving invalid persona state** | Save endpoint and GUI must both reject a config where a feature is enabled and its `requires` dependency is disabled. Auto-select alone is insufficient. |
| **Cached feature set format in Redis unspecified** | Store as `{"feature_key": true/false}` JSON dict. Writer and reader must agree on this format explicitly. |
| **`audit_log` table has no indexes** | Add indexes on `target_tenant_id`, `actor_id`, `timestamp` in the Alembic migration alongside table creation. |
| **`feature_overrides` NULL vs `{}` ambiguity** | Canonical DB default is `NULL`. Merge function must treat both `NULL` and `{}` identically. |
| **Multiple Redis round-trips per request for multi-gated routes** | Cache resolved feature dict in `request.state` on first `require_feature` call; subsequent calls within the same request read from state. |
| **Cycle detection at import raises wrong error type** | Raise `RuntimeError("Circular dependency in AVAILABLE_FEATURES requires graph: A → B → A")` at module level. This propagates as an `ImportError`, aborting FastAPI startup. Include the cycle path in the message for operator diagnosis. |
| **`GET /superadmin/features` response uncached at server** | Write a fresh value to Redis key `superadmin:features_registry` on every startup (not just cache miss). Add `Cache-Control: public, max-age=3600` as browser hint. |
| **`FeatureGate` undefined behavior on unknown key or during refresh** | Unknown key: fail closed + `console.warn` in production; throw error boundary in development. During background refresh: optimistic render from last known state (no flicker). |
| **Rollback does not flush `persona:tenants:*` or `superadmin:features_registry` keys** | Add steps to rollback: flush `persona:tenants:*`, `persona:features:*`, and `superadmin:features_registry`. |
| **Audit log rollback** | The audit_log table (or `UserActivity` extensions) must NOT be dropped on rollback — audit records are required for compliance in education/proctoring contexts. The rollback down-migration must explicitly skip the audit table. |
| **Redis Fan-out / Thundering Herd** | Implement jittered invalidation or background task queue for bulk invalidations. Add startup warm-up task (APScheduler) that pre-populates `persona:features:{tenant_id}` for all active tenants in batches of 100. |
| **Persona "Drift" (Snowflake Tenants)** | Monitor `snowflake_tenant_count` (tenants with non-null `feature_overrides`). Alert in Superadmin dashboard when count exceeds 20% of total active tenants — at that threshold, a new persona is likely a better solution than accumulated overrides. |
| **i18n Translation Bottleneck** | Allow "Default-to-English" keys during development; only enforce full 11-locale completeness as a pre-release gate or CI check. |
| **Middleware Overhead** | Cache `features_version` in `request.state`. Skip middleware entirely for unauthenticated requests. |
| **Invisible Prerequisite** | Startup validation asserts that all `requires` keys exist in `AVAILABLE_FEATURES_MAP` and that no key in `DEPRECATED_FEATURES` is referenced in any `requires` field. Runs as part of `FEATURE_DEPENDENCY_CLOSURE` pre-computation. |
| **`TierConfiguration.features` overlap** | Explicitly resolve before implementation: `TierConfiguration` gates hard resource limits; `PersonaConfiguration` gates UI feature visibility. Never gate the same key in both systems. |
| **`is_paid` validation has no subscription model** | `is_paid=True` features integrate with `TierService.get_tier_config()` using `min_tier` field. No new subscription model needed for v1. |
| **Two audit systems (`UserActivity` + new `audit_log`)** | Evaluate extending `UserActivity` before creating a new table. Document the decision; do not leave two parallel audit systems. |
| **`viewer` role absent from permission model** | Added to permission matrix. `viewer` can read `active_features` from `/me` but has no write access to any persona or override endpoint. |
| **Feature key rename leaves ghost keys** | Rename = deprecate old + add new + migration utility. CLI tool must include `rename-feature` subcommand. |
| **Cold-start stampede after Redis flush** | Startup background task (APScheduler) pre-populates `persona:features:{tenant_id}` in batches before first request is served. `Tenant.persona_id` index is mandatory for the rebuild query. |
| **Background task proctoring gap** | APScheduler jobs cannot use `Depends(require_feature)`. Provide a synchronous `get_tenant_features_sync(tenant_id)` utility for use inside scheduled jobs. Any background job with a feature dependency must call this explicitly — "silently assume all features enabled" is not acceptable for proctoring-related jobs. |
| **`require_feature` 403 body not distinguishable from role 403** | Return `{"detail": "feature_disabled", "feature": "<key>"}` on feature-gated denial. Frontend routes this to upsell flow; role-based 403 routes to access-denied. |
| **`Tenant.persona_id` FK missing index** | `index=True` on the `persona_id` column. Required for `SELECT id FROM tenants WHERE persona_id = ?` rebuild query and bulk seeding UPDATE. |
| **Dev override leakage to production** | Guard `?feature_override=` param with `import.meta.env.MODE === 'development'` (Vite build-time check). Code path is tree-shaken from production bundle. |
| **`DISABLE_FEATURE_GATING` untested and silent** | Add a test: set env var, assert all feature-gated routes return 200 for all roles. Log a `WARNING` at startup when env var is set so operators know the system is in degraded mode. |
| **Seeding loop incomplete** | Migration must loop `WHERE persona_id IS NULL LIMIT 500` until affected rows = 0. A single `LIMIT 500` without a loop is not a complete migration for tables with more than 500 rows. |
| **Clone inherits `is_active=True`** | Clone endpoint always sets `is_active=False` regardless of source state. Super_admin must explicitly activate after review. |
| **`<FeatureGate>` mode inconsistency** | Canonical mode values are `hide` (default), `disable`, `upsell`. These are the only valid values; all implementations must use them. |
| **`AVAILABLE_FEATURES` as list — O(n) key lookups** | Define `AVAILABLE_FEATURES_MAP: dict[str, dict] = {f["key"]: f for f in AVAILABLE_FEATURES}` in the same module. All programmatic key access uses the map; the list is for GUI ordering only. |
| **`require_feature` wrong DB session** | `require_feature` factory must declare `db: AsyncSession = Depends(get_async_db)` — never `get_db` (sync, Alembic-only). This is a known footgun per CLAUDE.md §2. |
| **`min_tier` absent from `AVAILABLE_FEATURES` schema** | Add `"min_tier": str` to the feature schema (required when `is_paid=True`). |
| **`features_version` integer overflow** | Column must be `BigInteger` (`BIGINT` in MySQL). A 32-bit `Integer` overflows immediately when storing Unix epoch ms (~1.7 trillion). |
| **`features_version` not incremented after deploy with new features** | Startup lifespan computes a hash of sorted feature keys, compares to `features_registry_hash` in Redis. If changed, bulk-sets `features_version = NOW_MS` for all active tenants and updates the hash. |
| **`superadmin:features_registry` not flushed on rollback** | Add to rollback flush list alongside `persona:features:*` and `persona:tenants:*`. |
| **DBA direct delete bypasses `features_version` and Redis invalidation** | `ON DELETE SET NULL` fires at DB level with no application code. After a DBA-level persona deletion, manually flush `persona:features:*` and bulk-set `features_version = NOW_MS` for affected tenants. Document in DBA runbook. |
| **Migration with live traffic** | `ADD COLUMN ... DEFAULT` on the `tenants` table is generally lock-free with InnoDB, but this is MySQL version-dependent. Specify whether the migration requires a maintenance window or can be run with live traffic. Consider `pt-online-schema-change` for large tables. |
| **Existing tests break when `require_feature` added to existing routes** | Before adding `Depends(require_feature(...))` to any existing route, update all tests for that route to include a default-persona fixture (tenant with `persona_id` set and valid Redis cache). Undeclared fixture dependencies will produce 403s that look like regressions. |
| **`X-Features-Version` middleware on unauthenticated requests** | Middleware must check for an authenticated user before any DB/Redis lookup. Routes without a JWT (login, health, public join) have no `tenant_id`; attempting lookup raises `AttributeError`. |
| **`actor_id` vs `user_id` naming conflict in audit schema** | Decide before migration: rename `user_id` → `actor_id` in `UserActivity` (breaking, requires updating all existing queries) or keep `user_id` and use `actor_id` only in new `audit_log` table. Do not mix both names in the same codebase. |
| **`UserActivity` retention pruning deletes unintended records** | If extending `UserActivity`, scope the pruning DELETE to persona/override actions only (e.g., `WHERE action IN ('persona_assign', ...) AND created_at < cutoff`). An unscoped delete removes login events and other records with different retention requirements. |

# Data Seeding

The system must not launch without at least one persona defined. Seed the following in the Alembic migration:

| slug | display_name | Notes |
|---|---|---|
| `default` | Default | Assigned to all existing tenants with `persona_id = NULL`. Includes all currently live features. |
| `education` | Education | Intended for schools/universities. |
| `corporate` | Corporate | Intended for enterprise/training use cases. |

**Seed all three personas with `features = {}` (empty JSON dict).** `AVAILABLE_FEATURES` is Python code, not DB data — the migration cannot reference it at migration time. An empty `features` dict is correct: the absent-key=`default_enabled` contract then handles all feature resolution from the live code registry, with no coupling between the migration and the feature list. Do not hardcode feature keys in the migration SQL.

After seeding, run a one-time UPDATE to assign `persona_id = (SELECT id FROM persona_configurations WHERE slug = 'default')` to all existing tenants where `persona_id IS NULL`.

**Table lock warning:** On a large tenants table, a single unbounded UPDATE holds a write lock for the duration of the statement. Execute this in a loop (`WHERE persona_id IS NULL LIMIT 500` repeated until affected rows = 0) to avoid blocking concurrent writes during migration. A single `LIMIT 500` without a loop does not complete the migration for tables exceeding 500 rows.

# NULL Persona Policy

If a tenant has no persona assigned (e.g., created before this migration, or persona was deleted), `require_feature` must fall back to the `default` persona's feature set. It must **never** raise a 403 solely because `persona_id` is NULL. The `default` persona must always exist and must always be the most permissive fallback.

**The "most permissive" requirement is advisory, not enforced.** Nothing in the schema or API validation prevents a super_admin from configuring the `default` persona with restrictive features, making the NULL fallback actively harmful. To enforce the intent: add a validation rule in the `default` persona save endpoint that rejects any configuration where a feature with `default_enabled=True` in `AVAILABLE_FEATURES` is set to `false`. Alternatively, document this as a convention and rely on the permission boundary and audit log to limit and track who modifies the `default` persona.

# Rollback Plan

If the migration or feature flag system causes a production regression:

1. The `persona_id` column is nullable — removing `Depends(require_feature(...))` from routes restores prior behavior.
2. To fully revert: run the down-migration to drop `persona_id`, `feature_overrides`, `features_version`, and the `persona_configurations` table.
3. Flush Redis keys matching `persona:features:*`.
4. Flush Redis keys matching `persona:tenants:*`.
5. Flush Redis key `superadmin:features_registry`.
6. **Do NOT drop the audit log table (or `UserActivity` extensions) during rollback.** Audit records are required for compliance in education/proctoring contexts and must be preserved regardless of whether the feature is rolled back. The down-migration must explicitly exclude audit log data.

**Critical rollback ordering:** Steps 1 and 2 must not be swapped. Routes decorated with `Depends(require_feature(...))` will throw HTTP 500 (not 403) the moment the down-migration drops the `persona_configurations` table, because SQLAlchemy will attempt to query a non-existent table. Always remove all `require_feature` decorators and redeploy first, then run the down-migration.

# Future Coding Guidelines
When building a new feature, developers must follow these steps:
1. **Register:** Add the new feature to `AVAILABLE_FEATURES` in `backend/core/constants/features.py`, including any `requires` dependencies. Run `python -m cli validate-features` before committing to catch cycle and missing-key errors.
2. **Frontend UI:** Wrap any new frontend components in `<FeatureGate requiredFeature="your_new_feature_key">`.
3. **Backend API:** Protect routes with `Depends(require_feature("your_new_feature_key"))`. **If adding `require_feature` to an existing route, update all existing tests for that route to include a default-persona fixture** — the dependency will return 403 for any test tenant without a valid persona, producing false-positive regression failures.
4. **i18n:** Add context variants to all locale files. Ensure fallback behavior is tested.
5. **Background tasks:** APScheduler jobs are not HTTP-request-scoped and cannot use `Depends(require_feature(...))`. Call `get_tenant_features_sync(tenant_id)` explicitly inside any scheduled job that has a feature dependency. Do not assume all features are enabled inside a scheduled job — this is especially critical for proctoring-related jobs where a tenant may not have proctoring enabled.
6. **User-Level Overrides:** User-level gating (e.g., for individual beta testers) is explicitly out of scope for v1. All gating is currently Tenant-level via Personas and Overrides. However, the architecture is designed to extend to `User.feature_overrides` by adding a third layer to the merge logic: `overrides[user]` > `overrides[tenant]` > `persona` > `default_enabled`.


# Persona Versioning & Point-in-Time Compliance

For education and proctoring use cases, it may be necessary to answer: "At the time student X took exam Y, what features were active for this tenant?" Audit logs of changes help reconstruct this but are not a substitute for a snapshot.

- When a tenant's persona is changed or `feature_overrides` are modified, write the **resolved feature set** (post-merge result, not just the delta) into the audit log row alongside the actor and timestamp. Store only the key→bool map, not the full `PersonaConfiguration` including display names, to keep row size manageable.
- This resolved snapshot must be stored even if the PersonaConfiguration itself is later modified, ensuring the historical record is immutable.
- Do not rely on replaying audit log deltas to reconstruct past state — store the full resolved set at change time.

# Verification & Testing
- Create automated backend tests for `require_feature` and `feature_overrides`.
- Test `require_feature` behavior when `persona_id IS NULL` (fallback logic).
- Verify that Redis cache invalidation works for both Persona and Tenant updates.
- **Test bulk cache invalidation:** Assign a persona to 3+ tenants, update the persona, and assert that all tenant cache keys are invalidated — not just the one triggering the update.
- **Test transitive `requires` resolution:** Create a chain A→B→C; disable C; assert that `require_feature("A")` returns 403.
- **Test `feature_overrides` validation:** Assert that sending an unknown key in `feature_overrides` returns HTTP 422.
- **Test `default` persona deletion guard:** Assert that attempting to DELETE or deactivate `slug='default'` returns an error.
- **Test `is_active=False` cascades:** Deactivate a persona; assert that all previously assigned tenants immediately resolve to the `default` feature set.
- **Test rollback ordering:** Assert that removing `Depends(require_feature)` decorators restores route access before the down-migration runs.
- **Run CI i18n completeness check:** Assert that every `AVAILABLE_FEATURES` key has a corresponding translation in all 11 locale files for every active persona context.
- **Test `features` JSON absent-key fallback:** Create a persona whose `features` JSON omits a key; assert that `require_feature` resolves it to `default_enabled` for that feature, not to disabled.
- **Test `feature_overrides` merge order:** Confirm that an override of `false` on a persona-enabled feature disables it, and an override of `true` on a persona-disabled feature enables it.
- **Test cycle detection:** Define a circular `requires` in `AVAILABLE_FEATURES` (A→B→A); assert that importing `features.py` raises `RuntimeError` with the cycle path in the message.
- **Test `super_admin` bypass:** Assert that a super_admin user passes `require_feature` even when their tenant's persona has the feature disabled.
- **Test Redis-down fallback:** Mock a Redis connection failure in `require_feature`; assert the route returns the correct feature decision (from DB) rather than a 500.
- **Test `GET /superadmin/features`:** Assert it returns all keys, display names, categories, requires, `is_paid`, and `min_tier` fields from `AVAILABLE_FEATURES` and is inaccessible to non-super_admin roles.
- **Test new tenant creation:** Create a tenant via the API; assert it has `persona_id` set to the `default` persona, `features_version > 0`, and appears in `persona:tenants:{default_id}` Redis set.
- **Test `X-Features-Version` header:** Assert it is present on authenticated API responses and its value increases when a persona is updated.
- **Test `X-Features-Version` absent on unauthenticated responses:** Assert that `POST /auth/login` and similar public endpoints do not include the `X-Features-Version` header and do not trigger DB/Redis lookups in the middleware.
- Test frontend `<FeatureGate>` and 403 interceptor logic.
- **Test 403 response body discrimination:** Assert that a feature-gated 403 returns `{"detail": "feature_disabled", "feature": "<key>"}` and a role-based 403 returns `{"detail": "Insufficient permissions"}`. Assert that the frontend interceptor routes each to the correct UX flow.
- Verify that the down-migration restores prior behavior.
- **Test `slug` UNIQUE constraint:** Attempt to insert two personas with the same slug; assert the DB raises a unique violation.
- **Test new persona `features` initialization:** Create a persona via the API; assert its `features` JSON contains every key in `AVAILABLE_FEATURES` pre-populated with the correct `default_enabled` value.
- **Test persona clone endpoint:** Clone a persona; assert the clone has identical `features`, a different `id`, the caller-supplied `slug` and `display_name`, and `is_active=False` regardless of the source's `is_active` state. Assert 422 if `slug` or `display_name` is missing from the request.
- **Test `GET /superadmin/personas/{id}/tenants`:** Assign 3 tenants to a persona; assert the endpoint returns exactly those 3 tenant IDs. Assert the endpoint supports pagination parameters.
- **Test persona reassignment atomic update:** Assign a tenant to persona A, then reassign to persona B; assert the tenant appears in `persona:tenants:{B_id}` and not in `persona:tenants:{A_id}`.
- **Test `FeatureGate` with an unknown feature key:** Render `<FeatureGate requiredFeature="nonexistent_key">`; assert it renders no children and emits a console warning in production mode; assert it throws an error boundary in development mode.
- **Test `features_version` is per-tenant:** Update the persona for tenant A; assert tenant B's `X-Features-Version` header is unchanged.
- **Test `features_version` is `BigInteger`-safe:** Assert that the column can store a current Unix epoch ms value (~1.7 trillion) without truncation.
- **Test `feature_overrides = {}` is equivalent to `feature_overrides = NULL`:** Assert both produce identical resolved feature sets.
- **Test `DISABLE_FEATURE_GATING=true` kill switch:** Set the env var; assert all feature-gated routes return 200 for all roles including non-super_admin users.
- **Test `DISABLE_FEATURE_GATING` startup warning:** Assert that a `WARNING` log entry is emitted at startup when the env var is set.
- **Test feature key rename migration:** Add a key to `DEPRECATED_FEATURES`; assert `require_feature` ignores it and returns the `default_enabled` value rather than 403.
- **Test `persona:tenants:*` TTL:** Assert the Redis set has a TTL set and is not unbounded.
- **Test seeding loop completeness:** In a migration test with >500 NULL tenants, assert all rows are updated, not just the first 500.
- **Test `features_version` increment on registry change:** Modify `AVAILABLE_FEATURES`, simulate a restart, assert that all tenant `features_version` values are updated to a new Unix epoch ms value.
- **Test existing routes after `require_feature` is added:** For each existing route that gains a `require_feature` decorator, assert existing tests still pass when a default-persona fixture is included, and return 403 when no persona is configured.
- **Load test `require_feature` under concurrency:** Add a locust scenario covering feature-gated routes at 100–500 concurrent users; establish a baseline latency budget for the added Redis round-trip.

# Operational Strategy & Lifecycle

## Feature Lifecycle & Graduation
- **Zombie Flag Prevention:** Every new feature should have a proposed "graduation date" or criteria (e.g., 100% adoption for 3 months).
- **Automated Flag Debt Reporting:** Add a weekly automated report (or Superadmin widget) that flags features that have been 100% enabled for all personas for more than 30 days, prompting developers to "Graduate" (delete) the flag.
- **Cleanup SOP:** Once graduated, the flag logic and `<FeatureGate>` wrappers should be removed from the codebase to maintain hygiene.

## Upsell vs. Hide Strategy
- **Marketing Mode:** The `<FeatureGate>` component supports a `mode` prop:
  - `hide` (default): Completely removes children.
  - `disable`: Renders children but applies a "disabled" state (e.g., greyed out).
  - `upsell`: Renders children but intercepts clicks to show a "Contact Sales" or "Upgrade" modal.

## Emergency Kill Switch
- **Global Bypass:** Implement an environment variable `DISABLE_FEATURE_GATING=true` that causes `require_feature` to always return `True`. This check is the very first line of `require_feature`. Emits a `WARNING` log at startup when active. Use only for production outage mitigation.

## Observability & Telemetry
- **Key Metrics to Track:**
  - `persona_cache_hit_rate` (Redis hits vs misses).
  - `persona_calculation_latency_ms`.
  - `snowflake_tenant_count` (Number of tenants with non-null `feature_overrides`).
  - **Drift alert threshold:** When `snowflake_tenant_count` exceeds 20% of total active tenants, surface a Superadmin dashboard alert recommending creation of a new persona rather than continued accumulation of individual overrides.

## UX for Dependency Cascades
- **Negative Cascades:** When a Superadmin disables a feature in the GUI, the system must detect and list all *dependent* features that will also be disabled, requiring a secondary confirmation step rather than just auto-selecting.

## Effective Permissions Debugger
- **Tooling:** Provide a Superadmin utility or CLI command `get_effective_features(tenant_id)` that outputs a table showing exactly where each feature's value originated (Persona vs. Override vs. Prerequisite failure).
