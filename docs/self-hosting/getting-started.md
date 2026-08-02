# Getting Started — Self-Hosting Swaya.me

This is the single walkthrough for taking a fresh clone of Swaya.me to a fully
working local copy: database, AI question-generation, and (optionally) the
coding-challenge sandbox VMs. If you just want the fastest possible path with
no AI/coding-challenge configuration, the [README Quick Start](../../README.md#quick-start-docker)
is shorter — this doc goes further and explains the *why* behind each step.

## What you end up with

| Component | Required? | Where it's configured |
|---|---|---|
| MySQL 8 + Redis 7 | Yes | `backend/.env` — `DB_*` / `REDIS_*` |
| Backend API (FastAPI) | Yes | `backend/.env` |
| Frontend (React/Vite) | Yes | `frontend/.env` (dev server proxies `/api`) |
| Google OAuth login | Optional | `backend/.env` — `GOOGLE_CLIENT_*` |
| Email (OTP, invites, reports) | Optional | `backend/.env` — `SMTP_*` |
| AI question generation / grading | Optional | `backend/.env` — `AI_*`, `GEMINI_*`/`OPENAI_*`/`ANTHROPIC_*`/`OLLAMA_*` — see [`ai.md`](ai.md) |
| Coding-challenge sandbox VMs | Optional | `backend/.env` — `CODER_*` — see [`coding-challenge-vms.md`](coding-challenge-vms.md) |

Everything under "Optional" degrades gracefully when unconfigured — the app
runs fine without any of it, the relevant buttons/endpoints just won't be
active (see "No-AI Mode" in `ai.md`, and the note in `coding-challenge-vms.md`).

---

## 1. Clone

```bash
git clone https://github.com/Chakrix-com/Swaya.me.git
cd Swaya.me
```

## 2. Bring up MySQL + Redis

Docker is the fastest way to get these two without installing them natively:

```bash
docker compose -f docker-compose.dev.yml up -d mysql redis
```

(You can run the backend/frontend from this same compose file too — see the
README's Quick Start — but most people doing active development run those two
natively for faster reload; that's what the rest of this doc assumes.)

## 3. Configure the backend

```bash
cd backend
cp .env.example .env
```

Open `.env` and fill in, at minimum:

| Variable | Value |
|---|---|
| `DB_PASSWORD` | `localpass` if you used the compose file above unmodified |
| `JWT_SECRET` | any long random string — `openssl rand -hex 32` |

Everything else in `.env.example` has a sane local default. Fill in the
optional sections as needed:

- **AI question generation** — get a free key at
  [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and
  set `GEMINI_KEY`. For other providers (OpenAI, Groq, Anthropic, local
  LM Studio/vLLM, Azure) or to understand the primary/light provider split,
  see [`ai.md`](ai.md).
- **Google OAuth login** — create credentials in
  [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
  and set `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`. Skip this and users can
  still register with email/password.
- **Email** (OTP verification, exam invites, PDF reports) — any SMTP provider
  works; set the `SMTP_*` vars. Skip this in local dev and those emails just
  won't send (functionality that depends on a verified email will be limited).
- **Coding-challenge sandbox VMs** — this is a separate piece of
  infrastructure (a Coder OSS server + Docker) beyond the main app. Only
  needed if you plan to use/test the `coding_challenge` quiz type. Full setup
  in [`coding-challenge-vms.md`](coding-challenge-vms.md).

## 4. Install dependencies and run migrations

```bash
# still in backend/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
```

## 5. Seed initial data

```bash
python scripts/seed_data.py
```

This creates the tier configuration rows and a demo super_admin account
(`demo@swaya.me` / `Demo1234`) you can log in with immediately. It's
idempotent — safe to re-run.

## 6. Run the backend

```bash
uvicorn main:app --reload --port 8000
```

API docs (Swagger UI): http://localhost:8000/api/docs
Health check: http://localhost:8000/api/health

## 7. Run the frontend

```bash
cd ../frontend
npm install
npm run dev
```

App: http://localhost:5173 — the Vite dev server proxies `/api` to
`localhost:8000` automatically, no extra config needed.

## 8. Log in

Use the seeded demo account (`demo@swaya.me` / `Demo1234`), or register a new
account through the UI. The demo account is `super_admin`, so it can also
assign the `CODING_CHALLENGE_PRO` per-user tier override to other users via
the admin panel (see `docs/multi-tenancy.md` for the tier system).

---

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest
```

The suite expects the database to be running and migrated (step 4 above) —
integration tests hit a real local database rather than mocking it.

## Next steps

- [`docs/architecture.md`](../architecture.md) — system overview, SSE realtime flow
- [`docs/multi-tenancy.md`](../multi-tenancy.md) — tenants, roles, tiers
- [`docs/deployment.md`](../deployment.md) — taking this to a production server
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — branch conventions, migration workflow, PR process
