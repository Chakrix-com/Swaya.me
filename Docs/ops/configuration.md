# Configuration

All environment variables are loaded from `.env` file via Pydantic BaseSettings (`backend/core/config/settings.py`).

---

## Database Settings (`DatabaseSettings`)

| Variable | Type | Default | Consumed In |
|---|---|---|---|
| `DB_HOST` | str | `localhost` | `settings.db.host`; `settings.db.url`, `settings.db.async_url` |
| `DB_PORT` | int | `3306` | `settings.db.port` |
| `DB_NAME` | str | `swaya_dev` | `settings.db.name` |
| `DB_USER` | str | `root` | `settings.db.user` |
| `DB_PASSWORD` | str | `""` | `settings.db.password` |
| `DB_POOL_SIZE` | int | `50` | `persistence/database_async.py`: `create_async_engine(pool_size=...)` |
| `DB_MAX_OVERFLOW` | int | `100` | `persistence/database_async.py`: `create_async_engine(max_overflow=...)` |
| `DB_POOL_RECYCLE` | int | `3600` | `persistence/database_async.py`: `create_async_engine(pool_recycle=...)` |

**Generated URLs** (computed properties, not env vars):
- Sync: `mysql+pymysql://{user}:{password}@{host}:{port}/{name}` — used only by Alembic migrations
- Async: `mysql+asyncmy://{user}:{password}@{host}:{port}/{name}` — used by all production async code

---

## Redis Settings (`RedisSettings`)

| Variable | Type | Default | Consumed In |
|---|---|---|---|
| `REDIS_HOST` | str | `localhost` | `settings.redis.host` |
| `REDIS_PORT` | int | `6379` | `settings.redis.port` |
| `REDIS_PASSWORD` | str | `""` | `settings.redis.password`; URL auth prefix if set |
| `REDIS_DB` | int | `0` | `settings.redis.db` |
| `REDIS_POOL_SIZE` | int | `50` | `shared/utils/redis_client.py`: `ConnectionPool.from_url(max_connections=...)` |

**Generated URL**: `redis://:{password}@{host}:{port}/{db}` or `redis://{host}:{port}/{db}` (if no password)

---

## JWT Settings (`JWTSettings`)

| Variable | Type | Default | Consumed In |
|---|---|---|---|
| `JWT_SECRET` | str | **REQUIRED — no default** | `core/security/jwt.py`: `create_access_token()`, `decode_access_token()` |
| `JWT_ALGORITHM` | str | `HS256` | `core/security/jwt.py` |
| `JWT_EXPIRATION_HOURS` | int | `24` | `core/security/jwt.py`: `timedelta(hours=settings.jwt.expiration_hours)` |

**Note**: `JWT_SECRET` has no default value — application will fail to start if not set.

---

## Application Settings (`AppSettings`)

| Variable | Type | Default | Consumed In |
|---|---|---|---|
| `HOST` | str | `0.0.0.0` | uvicorn bind address |
| `PORT` | int | `8000` | uvicorn port |
| `DEBUG` | bool | `False` | `main.py`: disables `TrustedHostMiddleware`; `database_async.py`: enables SQL echo |
| `RELOAD` | bool | `False` | uvicorn hot reload |
| `LOG_LEVEL` | str | `INFO` | NOT DERIVABLE in reviewed code — likely passed to uvicorn |
| `ENVIRONMENT` | str | `production` | `main.py` startup log; `email_service.py`: dev email fallback |
| `FRONTEND_URL` | str | `http://localhost:5173` | `core/auth/email_service.py`: verification and reset link URLs; `broker/api/auth.py`: Google OAuth redirect_uri |
| `ALLOWED_ORIGINS` | List[str] | `["http://localhost:3000"]` | `main.py`: `CORSMiddleware(allow_origins=...)` |

---

## Google OAuth Settings (`GoogleSettings`)

| Variable | Type | Default | Consumed In |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | str | `""` | `broker/api/auth.py`: `google_login()` and `google_callback()` |
| `GOOGLE_CLIENT_SECRET` | str | `""` | `broker/api/auth.py`: `google_callback()` token exchange |

**Note**: If `GOOGLE_CLIENT_ID` is empty, `GET /auth/google/login` returns HTTP 503.

---

## Email / SMTP Settings (consumed via `os.getenv()`, NOT via Pydantic settings)

These are read directly in `core/auth/email_service.py` using `os.getenv()`, NOT through the Pydantic settings class:

| Variable | Default | Consumed In |
|---|---|---|
| `SMTP_USER` | `""` | `email_service.py`: `MAIL_USERNAME` |
| `SMTP_PASSWORD` | `""` | `email_service.py`: `MAIL_PASSWORD` |
| `SMTP_FROM_EMAIL` | `info@chakrix.com` | `email_service.py`: `MAIL_FROM` |
| `SMTP_PORT` | `465` | `email_service.py`: `MAIL_PORT` |
| `SMTP_HOST` | `smtp.titan.email` | `email_service.py`: `MAIL_SERVER` |
| `SMTP_FROM_NAME` | `Swayame` | `email_service.py`: `MAIL_FROM_NAME` |

**Note**: If `SMTP_HOST`, `SMTP_USER`, or `SMTP_PASSWORD` are not set, `smtp_enabled=False` and emails are only logged. No error is thrown.

**IMPORTANT INCONSISTENCY**: These SMTP variables are read via `os.getenv()` outside the Pydantic settings system. They will NOT appear in the Settings class and are not validated at startup.

---

## Frontend Environment Variables

Consumed in `frontend/src/services/api.js` and build-time Vite substitution:

| Variable | Default | Consumed In |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | `api.js:3`: `import.meta.env.VITE_API_URL` → base URL for all API calls |

---

## Hardcoded Paths (NOT configurable via env)

Discovered from source code — these paths are hardcoded:

| Path | Where |
|---|---|
| `/home/vinay/Swaya.me/backend/uploads/images` | `main.py:lifespan()` — uploads dir |
| `/home/vinay/Swaya.me/backend/uploads/temp` | `main.py:lifespan()` — temp dir |
| `/home/vinay/Swaya.me/backend/uploads` | `main.py:create_application()` — StaticFiles mount |
| `/home/vinay/Swaya.me/backend/uploads/proctoring/{quiz_id}/{participant_id}` | `broker/api/proctoring.py:upload_snapshot()` |
| `http://127.0.0.1:11434` | `core/ai/ollama_service.py:OLLAMA_BASE_URL` — Ollama daemon |

These paths are machine-specific. Not suitable for containerized deployment without code changes.

---

## Runtime-Only Configuration (Redis keys)

These are not env vars but affect runtime behavior:

| Redis Key | TTL | Effect |
|---|---|---|
| `tier_config:{tier}` | 300s | Cached tier limits — changes to `tier_configurations` table take up to 5 min to propagate |
| `proctor:rules:{quiz_id}:{hash}` | 3600s | Cached rule set — proctoring rule changes take up to 1h to propagate to active sessions |

---

## Settings Class Structure

```python
# backend/core/config/settings.py

class Settings(BaseSettings):
    db: DatabaseSettings      # DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_POOL_*
    redis: RedisSettings      # REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB, REDIS_POOL_SIZE
    jwt: JWTSettings          # JWT_SECRET (required), JWT_ALGORITHM, JWT_EXPIRATION_HOURS
    app: AppSettings          # HOST, PORT, DEBUG, RELOAD, LOG_LEVEL, ENVIRONMENT, FRONTEND_URL, ALLOWED_ORIGINS
    google: GoogleSettings    # GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

settings = Settings()  # Global singleton; loaded once at import time
```

**Load behavior**: All sub-settings read from `.env` file at their own `env_file=".env"` config. The `.env` file must be in the working directory when uvicorn starts (i.e., `backend/` directory).
