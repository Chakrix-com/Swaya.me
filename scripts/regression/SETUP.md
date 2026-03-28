# Regression Suite Setup Guide

## One-time: Provision the regular-user test account

The regression suite requires a second test persona (`regression-free@swaya.me`, role=user, tier=FREE)
to exercise the non-admin code paths that are invisible to the `demo@swaya.me` super_admin account.

### Step 1 — Register the account

```bash
curl -X POST https://test.swaya.me/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"regression-free@swaya.me","full_name":"Regression Free User","password":"RegTest2026!"}'
```

The response will contain `"access_token": "pending_verification"` because email verification is required.

### Step 2 — Verify via database

Connect to the **test** MySQL database (`swayame_test`) and run:

```sql
UPDATE users SET is_email_verified = 1 WHERE email = 'regression-free@swaya.me';
```

### Step 3 — Confirm login works

```bash
curl -s -X POST https://test.swaya.me/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"regression-free@swaya.me","password":"RegTest2026!"}' | python3 -m json.tool
```

Expect a real JWT `access_token` (not `"pending_verification"`).

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `https://test.swaya.me/api/v1` | API base URL |
| `APP_BASE_URL` | `https://test.swaya.me` | Frontend base URL |
| `SELENIUM_URL` | `http://localhost:4444/wd/hub` | Selenium Grid URL |
| `HOST_EMAIL` | `demo@swaya.me` | Super-admin test account |
| `HOST_PASSWORD` | `Demo1234` | Super-admin password |
| `REGULAR_USER_EMAIL` | `regression-free@swaya.me` | Regular user test account |
| `REGULAR_USER_PASSWORD` | `RegTest2026!` | Regular user password |

---

## Running the full gate

```bash
BASE_URL=https://test.swaya.me/api/v1 \
APP_BASE_URL=https://test.swaya.me \
HOST_EMAIL=demo@swaya.me \
HOST_PASSWORD=Demo1234 \
REGULAR_USER_EMAIL=regression-free@swaya.me \
REGULAR_USER_PASSWORD=RegTest2026! \
bash scripts/regression/run_preprod_gate.sh
```

All 5 suites (A+B+C+D+E) must exit 0. Total expected time: ~4–6 minutes.

---

## Running individual suites

```bash
# Suite A: Release Smoke (~11s)
bash scripts/regression/run_smoke.sh

# Suite B: Core Functional Regression (~50s)
bash scripts/regression/run_core_regression.sh

# Suite C: Negative / Abuse Regression (~18s)
bash scripts/regression/run_negative_regression.sh

# Suite D: Extended Regression with Selenium (~90s) — requires selenium-arm container
bash scripts/regression/run_extended_regression.sh

# Suite E: UI Frontend Regression with Playwright (~90s)
bash scripts/regression/run_ui_regression.sh
```

---

## Prerequisites

- Python venv at `backend/.venv` with all packages installed:
  ```bash
  cd backend && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
  playwright install chromium
  ```
- Selenium container running for Suite D:
  ```bash
  sudo docker ps | grep selenium-arm
  # Start if needed:
  sudo docker start selenium-arm
  ```
- Test environment reachable at `https://test.swaya.me`

---

## Periodic maintenance

The regression suite creates and deletes test quizzes on every run. However, if a run is interrupted
mid-test, orphaned quizzes titled "RegTest *" or "Misc Endpoints Test Quiz" etc. may accumulate.

To clean up stale test quizzes on the test DB:

```sql
-- Preview
SELECT id, title, created_at FROM quizzes
WHERE title LIKE 'RegTest%'
  OR title LIKE '%Lifecycle Test%'
  OR title LIKE '%UI Test%'
  OR title LIKE '%Misc Endpoints%'
ORDER BY created_at;

-- Delete (review first!)
DELETE FROM quizzes
WHERE title LIKE 'RegTest%'
  OR title LIKE '%Lifecycle Test%'
  OR title LIKE '%UI Test%'
  OR title LIKE '%Misc Endpoints%';
```

---

## Suite structure

| Suite | Script | Tests |
|-------|--------|-------|
| A — Smoke | `run_smoke.sh` | API flow, session lifecycle, regular user login |
| B — Core | `run_core_regression.sh` | Regular user flows, folders/templates, offline poll, exam, admin API, misc endpoints |
| C — Negative | `run_negative_regression.sh` | Security checks, XSS guard, role boundaries, tenant isolation |
| D — Extended | `run_extended_regression.sh` | Selenium rejoin (admin + regular), word cloud E2E (admin + regular), offline poll E2E, exam E2E, rich text, dark mode |
| E — UI | `run_ui_regression.sh` | Playwright: quiz builder (regular + admin), audience flow, dashboard, auth pages |
