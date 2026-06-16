# Contributing to Swaya.me

Thank you for taking the time to contribute.

## Table of Contents

- [Local Development Setup](#local-development-setup)
- [Branch Conventions](#branch-conventions)
- [Making Changes](#making-changes)
- [Database Migrations](#database-migrations)
- [Running Tests](#running-tests)
- [Commit Format](#commit-format)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)

---

## AI Configuration

Swaya.me's AI features are powered by a pluggable provider system with two tiers:

- **Primary** (`AI_PRIMARY_PROVIDER`): question generation, exam analysis — use `gemini`, `openai_compat`, or `anthropic`
- **Light** (`AI_LIGHT_PROVIDER`): distractors, rewriting, answer grading — `ollama` (default, free, local) works well here

Minimum config (Gemini primary + local Ollama light):

```env
GEMINI_KEY=AIza...
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

> **Note:** Ollama is only supported as the light-tier provider. Do not set `AI_PRIMARY_PROVIDER=ollama`.

See [`docs/self-hosting/ai.md`](docs/self-hosting/ai.md) for the full provider matrix, `.env` examples for every supported backend, and model recommendations by RAM.

---

## Local Development Setup

Follow the [Quick Start](README.md#quick-start-docker) in the README to get the stack running. For active development, the native (non-Docker) setup is faster for hot-reload iteration.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in required values
alembic upgrade head
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` to `localhost:8000` automatically.

---

## Branch Conventions

| Prefix | Use |
|---|---|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `chore/` | Tooling, deps, config — no production code change |
| `docs/` | Documentation only |
| `refactor/` | Refactoring without behaviour change |
| `test/` | Adding or fixing tests |

Example: `feat/pdf-export`, `fix/webcam-stream-reinit`

Target the `main` branch for all PRs.

---

## Making Changes

### Backend

- All new services: use the async pattern (`*_service_async.py`). Sync versions (`*_service.py`) are legacy — do not add to them.
- New API endpoints: register them in `backend/broker/api/routes.py`.
- Config: add new settings to `backend/core/config/settings.py` as Pydantic fields with env-var aliases, and document them in `.env.example`.
- All new HTML from user input must pass through `shared/utils/html_sanitizer.sanitize_html()` or `sanitize_plain()` before storage.
- Rate-limit sensitive endpoints with `@limiter.limit("N/minute")` + `request: Request` parameter. See existing endpoints for the pattern.
- Role checks: use `Depends(require_admin)` or `Depends(require_super_admin)` — never compare `current_user.role` to a string literal.

### Frontend

- Feature components go under `frontend/src/features/<feature-name>/`.
- All API calls go through `frontend/src/services/api.js`.
- User-visible strings must use `t()` from `react-i18next`. Add the key to all 11 locale files under `frontend/src/locales/*/translation.json`.
- Do not translate database-stored content (question text, option text) — only UI chrome strings.
- Do not write to `localStorage` for anything security-sensitive. Auth is in HttpOnly cookies; exam session tokens belong in `sessionStorage`.

---

## Database Migrations

Migrations live in `backend/persistence/migrations/versions/`. Naming convention: `YYYYMMDD_HHMM_description.py`.

**Creating a new migration:**

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "add_column_to_quiz"
# Rename the generated file to follow YYYYMMDD_HHMM_description.py
# Review the generated file carefully before committing
alembic upgrade head   # verify it applies cleanly
```

Always review auto-generated migrations — autogenerate can miss complex changes (custom types, enum additions, multi-step transforms).

**Never modify an already-merged migration.** If you need to undo a schema change, create a new migration that reverts it.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Integration tests that hit a real local database are preferred over mocked unit tests. The test suite expects the database to be running and migrated.

When adding a feature, add tests alongside it. When fixing a bug, add a regression test that would have caught it.

---

## Commit Format

Commit messages follow the prefix convention:

```
feat: add team mode to live quiz
fix: resolve SSE disconnect on tab restore
chore: bump cryptography to 47.0.0
docs: add deployment guide
refactor: extract tier limit check into TierService
test: add regression test for OTP expiry
```

- First line: `<type>: <short description>` (present tense, lowercase after colon, under 72 chars)
- Leave a blank line before any additional body text
- Explain the **why** in the body, not the what — the diff already shows the what

---

## Submitting a Pull Request

1. Fork the repo and create your branch from `main`.
2. Make your changes, including tests.
3. Ensure `pytest` passes locally.
4. Run `npm run build` in `frontend/` and fix any TypeScript/lint errors.
5. Open a PR with a clear title and description explaining the **why**, not just the what.
6. Link to any relevant issues.

PR titles follow the same prefix convention as commits: `feat: ...`, `fix: ...`, etc.

---

## Reporting Bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) issue template. Include:
- Steps to reproduce
- Expected vs actual behaviour
- Browser / OS / Python version if relevant
- Any error output from the console or API logs

For security vulnerabilities, do **not** open a public issue — see [docs/security.md](docs/security.md#reporting-vulnerabilities).

---

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Please be respectful.
