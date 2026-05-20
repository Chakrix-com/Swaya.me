# Contributing to Swaya.me

Thank you for taking the time to contribute.

## Table of Contents

- [Local Development Setup](#local-development-setup)
- [Branch Conventions](#branch-conventions)
- [Making Changes](#making-changes)
- [Running Tests](#running-tests)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)

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
- New database columns or tables: create an Alembic migration with the format `YYYYMMDD_HHMM_description.py`.
- New API endpoints: register them in `backend/broker/api/routes.py`.
- Config: add new settings to `backend/core/config/settings.py` as Pydantic fields with env-var aliases, and document them in `.env.example`.

### Frontend

- Feature components go under `frontend/src/features/<feature-name>/`.
- All API calls go through `frontend/src/services/api.js`.
- User-visible strings must use `t()` from `react-i18next`. Add the key to all 11 locale files under `frontend/src/locales/*/translation.json`.
- Do not translate database-stored content (question text, option text, etc.) — only UI chrome strings.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

When adding a feature, add tests alongside it. Integration tests that hit a real (local) database are preferred over mocked unit tests.

---

## Submitting a Pull Request

1. Fork the repo and create your branch from `main`.
2. Make your changes, including tests.
3. Ensure `pytest` passes locally.
4. Open a PR with a clear title and description explaining the **why**, not just the what.
5. Link to any relevant issues.

PR titles should follow the same prefix convention as branches: `feat: ...`, `fix: ...`, etc.

---

## Reporting Bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) issue template. Include:
- Steps to reproduce
- Expected vs actual behaviour
- Browser / OS / Python version if relevant
- Any error output from the console or API logs

---

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Please be respectful.
