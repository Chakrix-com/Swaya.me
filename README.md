# Swaya.me — Live Audience Engagement Platform

Swaya is an open-source, multi-tenant platform for running live quizzes, polls, word clouds, and proctored exams. Audiences join instantly via QR code or join code — no app, no login required.

**Live demo:** [www.swaya.me](https://www.swaya.me)

---

## Features

- **Live Quiz** — Real-time competitive quizzes with instant leaderboards
- **Live Poll** — Gather audience feedback with live result visualization
- **Word Cloud** — Crowd-sourced responses rendered as a live word cloud with automatic profanity filtering
- **Offline Poll** — QR-code-based polling for physical spaces without an active host
- **Exam Mode** — Self-paced, timed exams with webcam proctoring, OTP email verification, and PDF reports
- **AI Question Generation** — Generate localized MCQ quizzes from a single prompt (Gemini)
- **AI Result Analysis** — Post-exam AI summary of class performance
- **11 languages** — UI and AI-generated content in English, Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati, Spanish, French, German, Russian
- **Multi-tenant** — Each tenant gets isolated data, branding, and tier-based limits (Free / Basic / Pro / Enterprise)
- **Export** — Results to PDF, Excel, and PowerPoint

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), Alembic, Python 3.10+ |
| Frontend | React 18, Vite 5, Ant Design 5, Redux Toolkit, react-i18next |
| Database | MySQL 8 |
| Cache / Pub-Sub | Redis 7 |
| AI | Google Gemini (question generation, result analysis) |
| Auth | JWT + Google OAuth 2.0 |
| Real-time | WebSockets (FastAPI native) |
| Email | SMTP (configurable — Titan, SendGrid, etc.) |

---

## Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone & configure

```bash
git clone https://github.com/Chakrix-com/Swaya.me.git
cd Swaya.me
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in at minimum:
- `JWT_SECRET` — any long random string
- `GEMINI_KEY` — Google AI Studio API key (free tier works)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — for Google OAuth (optional)
- `SMTP_*` — for email features (optional)

### 2. Start services

```bash
docker compose -f docker-compose.dev.yml up --build
```

This starts MySQL, Redis, and the FastAPI backend with hot-reload.

### 3. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173  
API docs: http://localhost:8000/api/docs

### 4. Apply database migrations

```bash
docker exec swaya-dev-backend alembic upgrade head
```

---

## Manual Setup (without Docker)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit as above
alembic upgrade head
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
Swaya.me/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── broker/api/routes.py       # Central router
│   ├── core/
│   │   ├── config/settings.py     # All config (env-driven)
│   │   ├── ai/                    # Gemini + Ollama integrations
│   │   └── security/              # JWT, OAuth, password hashing
│   ├── features/
│   │   └── quiz/                  # Quiz, session, exam, poll services
│   ├── persistence/
│   │   ├── models/                # SQLAlchemy models
│   │   └── migrations/            # Alembic migrations
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Root routes + ProLayout
│   │   ├── features/              # Feature slices (quiz, auth, admin…)
│   │   ├── services/api.js        # All API calls
│   │   └── locales/               # i18n JSON files (11 languages)
│   └── .env.production
├── docker-compose.dev.yml
└── scripts/                       # Load tests, regression scripts
```

---

## Environment Variables

Copy `backend/.env.example` and fill in the values. Key variables:

| Variable | Required | Description |
|---|---|---|
| `DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Yes | MySQL connection |
| `REDIS_HOST` / `REDIS_PORT` | Yes | Redis connection |
| `JWT_SECRET` | Yes | Random secret for JWT signing |
| `GEMINI_KEY` | For AI features | Google AI Studio API key |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | For Google login | OAuth 2.0 credentials |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | For email | Any SMTP provider |
| `SMTP_FROM_EMAIL` / `SMTP_FROM_NAME` | For email | Sender identity |
| `FRONTEND_URL` | For email links | Your deployed frontend URL |
| `OLLAMA_BASE_URL` | Optional | Local Ollama for offline AI |

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

---

## API Documentation

Interactive Swagger UI is available at `/api/docs` when the backend is running.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, branch conventions, and PR guidelines.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

Copyright 2026 Chakrix / Nishant
