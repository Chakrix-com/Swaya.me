# Antigravity Review: Personas & Feature Flag Architecture

> **Reviewed:** `Docs/personas_implementation.md`  
> **Date:** 2026-04-26  
> **Reviewer:** Antigravity (AI Code Assistant)

---

## Overall Assessment

The plan is **well-conceived and directionally sound**. It cleanly separates configuration from code and aligns with established multi-tenancy patterns already present in the codebase. The `FeatureGate` / `require_feature` symmetry across frontend and backend is the right abstraction. The "Future Coding Guidelines" section in particular is the most important part — enforcing the 4-step pattern is what will prevent the `if persona == 'x'` anti-pattern from creeping in.

Several gaps exist where the plan meets the actual codebase. These should be resolved before execution begins to avoid mid-implementation rework.

---

## ✅ What the Plan Gets Right

| Aspect | Why It's Good |
|---|---|
| **Separation of concerns** | Persona config lives in the DB, not in `if/else` chains. Clean runtime boundary. |
| **Central feature registry** | A single `AVAILABLE_FEATURES` source of truth makes the superadmin GUI self-updating and prevents orphaned feature keys. |
| **Reuses existing i18n** | The `t('participant', { context: user.i18nContext })` pattern is idiomatic `react-i18next` and avoids duplicating full translation files. |
| **Developer workflow** | The 4-step coding rule is explicit and enforceable — the hardest part of feature-flag systems to get right. |
| **Superadmin GUI** | Exposing `AVAILABLE_FEATURES` as a GET endpoint so the UI matrix is always in sync is a smart design choice. |

---

## ⚠️ Gaps & Issues Found

### 1. Conceptual Overlap: `PersonaConfiguration.features` vs. `TierConfiguration.features`

**File:** `backend/persistence/models/core.py` — `TierConfiguration` (line 132)

There is already a `TierConfiguration` model with a `features` column (a JSON string). The plan introduces a second `features` concept on `PersonaConfiguration` without acknowledging the existing one.

**Risk:** A tenant on a `FREE` tier could theoretically hold a persona that grants features their tier doesn't allow. The two systems may silently conflict.

**Action required:** Define the boundary explicitly before writing any model code:
- **Tier** → controls *capacity limits* (max participants, max questions, concurrent events)
- **Persona** → controls *UI behaviour and domain terminology*

If this is the intended boundary, state it clearly in the spec. If `TierConfiguration.features` is being deprecated, that is a breaking migration.

---

### 2. `dependencies.py` Target Location Is Inconsistent with Existing Code

**Plan target:** `backend/core/security/dependencies.py`  
**Existing pattern:** `get_current_user` lives in `backend/core/auth/dependencies.py`

The `security/` module currently only contains `jwt.py` and `password.py`. Adding `require_feature` there breaks the established convention where auth dependencies live under `core/auth/`.

**Recommendation:** Add `require_feature` to `backend/core/auth/dependencies.py` for consistency, or create `core/security/dependencies.py` with a documented rationale for the split.

---

### 3. `active_features` Delivery Strategy Is Unspecified

The plan says to "modify the login/user-profile API to return `active_features`" but does not commit to *how*.

**Two options:**

| Approach | Pros | Cons |
|---|---|---|
| **Embed in JWT payload** | Zero extra DB call per request | Features are stale until token refresh |
| **Return in login response body** | Always reflects current config | Must be re-fetched on token refresh |

**Recommendation:** Include `active_features` and `i18n_context` in the `UserResponse` schema returned alongside the token at login. This is consistent with how `role` and `tier` are already surfaced in the existing `/auth/me` endpoint, avoids JWT bloat, and fits naturally into the `authSlice.loginSuccess` payload.

---

### 4. Redux State Shape for `activeFeatures` Is Undefined

**File:** `frontend/src/store/authSlice.js`

The current slice stores `user`, `token`, `isAuthenticated`, `loading`, `error`. The plan mentions updating Redux state but leaves the shape unspecified.

**Issue:** If `activeFeatures` is nested inside `state.user`, `FeatureGate` becomes coupled to the user object shape and `localStorage` serialisation must handle it.

**Recommendation:** Add `activeFeatures` and `i18nContext` as **top-level fields** in `authSlice`:

```js
const initialState = {
  user: ...,
  token: ...,
  isAuthenticated: ...,
  activeFeatures: JSON.parse(localStorage.getItem('activeFeatures') || '[]'),
  i18nContext: localStorage.getItem('i18nContext') || null,
  ...
}
```

This keeps `FeatureGate` selectors clean (`state.auth.activeFeatures`) and makes `localStorage` persistence explicit.

---

### 5. i18n Context Requires Changes to All 11 Locale Files

**File:** `frontend/src/locales/i18n.js` — 11 language directories exist (en, hi, ta, te, ka, bn, gu, es, fr, ru, de)

The `react-i18next` context feature works by looking for keys with a `_<context>` suffix (e.g., `participant_education`, `participant_healthcare`) inside each locale's `translation.json`.

**The plan does not mention this work.** Adding persona terminology means touching every locale file for every persona-specific term. This is non-trivial, especially for non-English locales which may require translation.

**Action required:** Scope this work explicitly. A practical first version could limit i18n context support to English only and expand to other locales incrementally.

---

### 6. No Mention of Cache Invalidation / Stale Feature Flags

If `activeFeatures` is stored in `localStorage` and Redux on login, changing a persona config in the Superadmin GUI will **not take effect until the user logs out and back in** (or at minimum, refreshes the page).

The plan's Verification section mentions "page refresh" but does not acknowledge this as a UX limitation.

**Recommendation:** Document this explicitly as a known V1 limitation. If real-time propagation is ever required, a WebSocket broadcast or a `/auth/me` polling mechanism can be added — but that is out of scope for the initial implementation.

---

### 7. `frontend/src/features/superadmin/` Does Not Exist

**Current feature directories:** `admin`, `audience`, `auth`, `dashboard`, `exam`, `home`, `offline-poll`, `proctoring`, `quiz`

There is no `superadmin` feature directory. More importantly, the existing `admin` feature likely overlaps in scope.

**Action required:** Clarify whether:
- The Persona Management UI lives inside the existing `admin` feature (as a superadmin-only section), or
- A separate `superadmin` feature directory is created with its own routing and role guard.

---

## 📋 Prioritised Pre-Implementation Checklist

- [ ] **Define Tier vs. Persona boundary** in the spec before touching models
- [ ] **Choose `dependencies.py` location** (`core/auth/` recommended)
- [ ] **Commit to `active_features` delivery strategy** (login response body recommended)
- [ ] **Define Redux state shape** (top-level fields recommended)
- [ ] **Scope i18n context work** — V1 English-only is a reasonable starting point
- [ ] **Document stale feature limitation** explicitly in the spec
- [ ] **Clarify superadmin vs. admin frontend routing**

---

## Verdict

The architecture is the right call for a growing multi-tenant platform. Fix the boundary and state-shape questions above and this is ready to execute.
