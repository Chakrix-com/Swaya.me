# Plan: Isolate Persona App from Swaya.me

**Status:** `NOT STARTED`  
**Last updated:** —  
**Executed by:** —  
**Resume from:** Phase 1, Step 1

---

## ⛔ NON-NEGOTIABLE CONSTRAINT

**`test.swaya.me` and `www.swaya.me` must remain fully operational at all times during and after this isolation work. Any action that breaks either site is a hard blocker — stop immediately and revert.**

### What this means in practice

| Rule | Detail |
|------|--------|
| **No code changes on `main` branch** | All persona implementation work is committed exclusively to the `persona` branch. Zero commits to `main` as part of this plan. |
| **No edits to existing systemd services** | `swayame-backend-test.service` and `swayame-backend.service` are read-only. Do not restart, modify, or touch them at any point. |
| **No edits to existing nginx configs** | `test.swaya.me.conf` and `www.swaya.me.conf` are read-only. New persona configs are separate files. |
| **No edits to existing databases** | `swayame_test` and `swayame` databases are untouched. Only new databases (`swayame_persona_dev`, `swayame_persona`) are created. |
| **No edits to existing `.env` files** | `/home/vinay/Swaya.me/backend/.env` and `/www/wwwroot/swaya-live/backend/.env` are read-only. |
| **No changes to shared Redis DB 0** | All persona Redis keys use DB 1 (dev) and DB 2 (prod). Never write to DB 0 from persona code. |
| **No nginx reload without a config test first** | Always run `sudo /www/server/nginx/sbin/nginx -t` and confirm it reports `syntax is ok` before reloading. A bad nginx config file takes down both sites. |
| **Verify both sites after any nginx reload** | After every `nginx -s reload`, immediately check `curl -sf https://test.swaya.me/health` and `curl -sf https://www.swaya.me/health` before continuing. |
| **`git worktree add` does not affect `main`** | The worktree command only adds a new checkout path — it does not change any files in `/home/vinay/Swaya.me/` or its branch. |

### Pre-execution health baseline

Before starting Phase 1, record that both sites are healthy. If either returns a failure, **do not proceed** — investigate and resolve first.

```bash
curl -sf http://127.0.0.1:8001/health && echo "test OK" || echo "test FAILED"
curl -sf http://127.0.0.1:8000/health && echo "live OK" || echo "live FAILED"
```

---

## Context
The persona implementation (v9 doc) is a major architectural addition that will diverge significantly from the main codebase. The goal is two completely independent apps:
- **swaya.me** — existing app, unchanged
- **persona.swaya.me** — new app for persona/feature-flag implementation, with its own dev and prod environments

This means separate git branch, separate databases, separate Redis DBs, separate ports, separate systemd services, separate nginx configs, and a separate deploy script.

---

## Port Assignment Rule

**Always verify a port is free before assigning it.** This server runs multiple apps and many ports in the 8xxx range are already occupied. Before choosing any new port, run:

```bash
sudo ss -tlnp | grep ':<port>'
# or to see all occupied ports at once:
sudo ss -tlnp | awk '{print $4}' | grep -oP ':\K\d+' | sort -n | uniq
```

**Known occupied ports as of 2026-04-30:**

| Port | Process |
|------|---------|
| 80, 443 | nginx |
| 888, 887 | nginx |
| 8000 | uvicorn — swaya.me live backend |
| 8001 | uvicorn — swaya.me test backend |
| 8002 | uvicorn — unknown app |
| 8005 | python3 — unknown app |
| 8010 | uvicorn — unknown app |
| 8188, 8190 | litespeed |
| 9000, 9001 | docker-proxy |
| 4444, 7900 | docker-proxy (selenium) |
| 7080 | litespeed |
| 11434 | ollama |

This list reflects a point-in-time snapshot. **Re-run `ss -tlnp` before each new port assignment** — do not rely on this table alone.

---

## Architecture Overview

| Dimension | swaya.me (existing) | persona.swaya.me (new) |
|---|---|---|
| Dev URL | test.swaya.me | dev.persona.swaya.me |
| Prod URL | www.swaya.me | persona.swaya.me |
| Dev source code | `/home/vinay/Swaya.me/` (branch: `main`) | `/www/wwwroot/dev.persona.swaya.me/` (branch: `persona`) |
| Prod backend | `/www/wwwroot/swaya-live/backend/` | `/www/wwwroot/persona-live/backend/` |
| Prod frontend | `/www/wwwroot/www.swaya.me/` | `/www/wwwroot/persona.swaya.me/` |
| Backend port (dev) | 8001 | **8003** |
| Backend port (prod) | 8000 | **8004** |
| Database (dev) | `swayame_test` | `swayame_persona_dev` |
| Database (prod) | `swayame` | `swayame_persona` |
| Redis DB | 0 (both envs) | **1** (dev) / **2** (prod) |
| Git branch | `main` | `persona` |
| Dev systemd | `swayame-backend-test.service` | `swayame-persona-dev.service` |
| Prod systemd | `swayame-backend.service` | `swayame-persona.service` |

---

## Git Isolation Strategy: Worktree

Use `git worktree` — single git repo at `/home/vinay/Swaya.me/`, two branches (`main` and `persona`) checked out simultaneously at different paths. This is preferable over a separate clone because:
- Single remote — no duplicate push/fetch complexity
- Release tags and history are shared
- Cherry-picks from `main` → `persona` are trivial
- Each worktree has its own HEAD, staging area, and uncommitted state

```
/home/vinay/Swaya.me/              ← primary worktree  (branch: main)
/www/wwwroot/dev.persona.swaya.me/ ← linked worktree   (branch: persona)
```

---

## Critical Files & Paths

### To Create
- `/www/wwwroot/dev.persona.swaya.me/backend/.env` — persona dev backend config
- `/www/wwwroot/dev.persona.swaya.me/frontend/.env.production` — persona dev frontend config (same as main: `VITE_API_URL=/api/v1`)
- `/www/wwwroot/persona-live/backend/.env` — persona live backend config
- `/etc/systemd/system/swayame-persona-dev.service` — new systemd service (port 8003)
- `/etc/systemd/system/swayame-persona.service` — new systemd service (port 8004)
- `/www/server/panel/vhost/nginx/dev.persona.swaya.me.conf` — nginx config (mirrors `test.swaya.me.conf`)
- `/www/server/panel/vhost/nginx/persona.swaya.me.conf` — nginx config (mirrors `www.swaya.me.conf`)
- `/www/wwwroot/dev.persona.swaya.me/persona-deploy.sh` — standalone deploy script for persona app

### Existing Files to Know About
- `/home/vinay/Swaya.me/deploy.sh` — existing deploy script (for swaya.me only, **not touched**)
- `/home/vinay/Swaya.me/backend/core/config/settings.py:82` — `UPLOADS_BASE_DIR` env var controls uploads path (must be overridden in persona `.env`)
- `/home/vinay/Swaya.me/backend/main.py:117` — `TrustedHostMiddleware` already allows `*.swaya.me`, covers persona domains — no change needed

---

## Execution Phases

> **How to resume:** Find the first unchecked `[ ]` step. Update the **Resume from** field at the top of this file when pausing.

---

### Phase 1 — Git Setup
**Status:** `[ ] Not started`

- [ ] **1.1** Verify current branch is `main`: `git -C /home/vinay/Swaya.me branch --show-current`
- [ ] **1.2** Create `persona` branch from current HEAD of `main`:
  ```bash
  git -C /home/vinay/Swaya.me checkout -b persona
  git -C /home/vinay/Swaya.me checkout main
  ```
- [ ] **1.3** Confirm both branches exist: `git -C /home/vinay/Swaya.me branch`
- [ ] **1.4** Clear aaPanel placeholder files from target path (preserve `.well-known` for SSL):
  ```bash
  sudo rm -f /www/wwwroot/dev.persona.swaya.me/index.html \
             /www/wwwroot/dev.persona.swaya.me/404.html \
             /www/wwwroot/dev.persona.swaya.me/502.html \
             /www/wwwroot/dev.persona.swaya.me/.htaccess \
             /www/wwwroot/dev.persona.swaya.me/.user.ini
  ```
- [ ] **1.5** Add worktree — checks out `persona` branch at the dev persona path:
  ```bash
  git -C /home/vinay/Swaya.me worktree add /www/wwwroot/dev.persona.swaya.me persona
  ```
- [ ] **1.6** Fix ownership (services run as user `vinay`):
  ```bash
  sudo chown -R vinay:vinay /www/wwwroot/dev.persona.swaya.me
  ```
- [ ] **1.7** Verify: `git -C /home/vinay/Swaya.me worktree list` — shows both paths

---

### Phase 2 — Databases
**Status:** `[ ] Not started`

- [ ] **2.1** Verify `swayame_user` exists: `mysql -u root -p -e "SELECT User, Host FROM mysql.user WHERE User='swayame_user';"`
- [ ] **2.2** Create persona databases (run via aaPanel SQL tool or `mysql -u root -p`):
  ```sql
  CREATE DATABASE swayame_persona_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE DATABASE swayame_persona CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  GRANT ALL PRIVILEGES ON swayame_persona_dev.* TO 'swayame_user'@'localhost';
  GRANT ALL PRIVILEGES ON swayame_persona.* TO 'swayame_user'@'localhost';
  FLUSH PRIVILEGES;
  ```
- [ ] **2.3** Verify: `mysql -u swayame_user -p -e "SHOW DATABASES;" | grep persona`

---

### Phase 3 — Python venv for Persona Dev
**Status:** `[ ] Not started`

- [ ] **3.1** Create venv:
  ```bash
  cd /www/wwwroot/dev.persona.swaya.me/backend
  python3 -m venv .venv
  ```
- [ ] **3.2** Install requirements:
  ```bash
  /www/wwwroot/dev.persona.swaya.me/backend/.venv/bin/pip install -r requirements.txt -q
  ```
- [ ] **3.3** Verify: `.venv/bin/python --version` and `.venv/bin/uvicorn --version`

---

### Phase 4 — Backend `.env` for Persona Dev
**Status:** `[ ] Not started`

- [ ] **4.1** Generate a new JWT secret: `openssl rand -hex 32`
- [ ] **4.2** Create `/www/wwwroot/dev.persona.swaya.me/backend/.env`:
  ```ini
  # Database
  DB_HOST=localhost
  DB_PORT=3306
  DB_NAME=swayame_persona_dev
  DB_USER=swayame_user
  DB_PASSWORD=Sw4y4m3_S3cur3_P4ssw0rd!2026
  DB_POOL_SIZE=10
  DB_MAX_OVERFLOW=40

  # Redis — DB 1 isolates persona from main app (main uses DB 0)
  REDIS_HOST=localhost
  REDIS_PORT=6379
  REDIS_DB=1

  # JWT — distinct secret from main app (generated in step 4.1)
  JWT_SECRET=<value from step 4.1>
  JWT_ALGORITHM=HS256
  JWT_EXPIRATION_HOURS=24

  # App
  PORT=8003
  DEBUG=False
  ENVIRONMENT=production
  UPLOADS_BASE_DIR=/www/wwwroot/dev.persona.swaya.me/backend/uploads
  BASE_URL=https://dev.persona.swaya.me
  FRONTEND_URL=https://dev.persona.swaya.me
  ALLOWED_ORIGINS=dev.persona.swaya.me,localhost

  # SMTP (same credentials as main)
  SMTP_HOST=smtp.titan.email
  SMTP_PORT=465
  SMTP_USER=info@chakrix.com
  SMTP_PASSWORD=<copy from /home/vinay/Swaya.me/backend/.env>
  SMTP_FROM_EMAIL=info@chakrix.com
  SMTP_FROM_NAME=Persona Swaya

  # Google OAuth (same credentials as main)
  GOOGLE_CLIENT_ID=684826739028-f7m11k740ioud1q9q368ad49fise9kav.apps.googleusercontent.com
  GOOGLE_CLIENT_SECRET=<copy from /home/vinay/Swaya.me/backend/.env>
  ```
- [ ] **4.3** Verify file is not world-readable: `chmod 600 /www/wwwroot/dev.persona.swaya.me/backend/.env`

---

### Phase 5 — Alembic Migrations for Persona Dev DB
**Status:** `[ ] Not started`

- [ ] **5.1** Run migrations against `swayame_persona_dev`:
  ```bash
  cd /www/wwwroot/dev.persona.swaya.me/backend
  PYTHONPATH=/www/wwwroot/dev.persona.swaya.me/backend \
    .venv/bin/alembic upgrade head
  ```
- [ ] **5.2** Verify: `mysql -u swayame_user -p swayame_persona_dev -e "SHOW TABLES;"` — should show all app tables

---

### Phase 6 — Frontend Setup for Persona Dev
**Status:** `[ ] Not started`

- [ ] **6.1** Install node dependencies:
  ```bash
  npm install --prefix /www/wwwroot/dev.persona.swaya.me/frontend
  ```
- [ ] **6.2** Confirm `.env.production` has correct value (already in branch — no change needed):
  ```
  VITE_API_URL=/api/v1
  ```
- [ ] **6.3** Build frontend:
  ```bash
  npm --prefix /www/wwwroot/dev.persona.swaya.me/frontend run build
  ```
- [ ] **6.4** Fix permissions for nginx:
  ```bash
  chmod -R a+rX /www/wwwroot/dev.persona.swaya.me/frontend/dist
  ```
- [ ] **6.5** Verify: `ls /www/wwwroot/dev.persona.swaya.me/frontend/dist/` — should show `index.html` and `assets/`

---

### Phase 7 — Persona Live Directory
**Status:** `[ ] Not started`

- [ ] **7.1** Create live backend directory:
  ```bash
  mkdir -p /www/wwwroot/persona-live/backend
  sudo chown -R vinay:vinay /www/wwwroot/persona-live
  ```
- [ ] **7.2** Create `/www/wwwroot/persona-live/backend/.env`:
  ```ini
  DB_HOST=localhost
  DB_PORT=3306
  DB_NAME=swayame_persona
  DB_USER=swayame_user
  DB_PASSWORD=Sw4y4m3_S3cur3_P4ssw0rd!2026
  DB_POOL_SIZE=50
  DB_MAX_OVERFLOW=100
  REDIS_HOST=localhost
  REDIS_PORT=6379
  REDIS_DB=2
  JWT_SECRET=<same as dev .env, or generate a separate one>
  JWT_ALGORITHM=HS256
  JWT_EXPIRATION_HOURS=24
  PORT=8004
  DEBUG=False
  ENVIRONMENT=production
  UPLOADS_BASE_DIR=/www/wwwroot/persona-live/backend/uploads
  BASE_URL=https://persona.swaya.me
  FRONTEND_URL=https://persona.swaya.me
  ALLOWED_ORIGINS=persona.swaya.me
  SMTP_HOST=smtp.titan.email
  SMTP_PORT=465
  SMTP_USER=info@chakrix.com
  SMTP_PASSWORD=<copy from /home/vinay/Swaya.me/backend/.env>
  SMTP_FROM_EMAIL=info@chakrix.com
  SMTP_FROM_NAME=Persona Swaya
  GOOGLE_CLIENT_ID=684826739028-f7m11k740ioud1q9q368ad49fise9kav.apps.googleusercontent.com
  GOOGLE_CLIENT_SECRET=<copy from /home/vinay/Swaya.me/backend/.env>
  ```
- [ ] **7.3** Secure the file: `chmod 600 /www/wwwroot/persona-live/backend/.env`

  > **Note:** The live Python venv and first migration run are handled by `persona-deploy.sh promote-live` (Phase 10). No manual venv setup needed here.

---

### Phase 8 — Systemd Services
**Status:** `[ ] Not started`

- [ ] **8.1** Create `/etc/systemd/system/swayame-persona-dev.service`:
  ```ini
  [Unit]
  Description=Swaya.me Persona Backend API (Dev)
  After=network.target mysql.service redis.service

  [Service]
  Type=simple
  User=vinay
  Group=vinay
  WorkingDirectory=/www/wwwroot/dev.persona.swaya.me/backend
  Environment=PATH=/www/wwwroot/dev.persona.swaya.me/backend/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
  Environment=PYTHONPATH=/www/wwwroot/dev.persona.swaya.me/backend
  EnvironmentFile=/www/wwwroot/dev.persona.swaya.me/backend/.env
  ExecStart=/www/wwwroot/dev.persona.swaya.me/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8003 --workers 2
  Restart=on-failure
  RestartSec=5
  StandardOutput=append:/var/log/swayame-persona-dev.log
  StandardError=append:/var/log/swayame-persona-dev-error.log
  NoNewPrivileges=true
  PrivateTmp=true

  [Install]
  WantedBy=multi-user.target
  ```

- [ ] **8.2** Create `/etc/systemd/system/swayame-persona.service`:
  ```ini
  [Unit]
  Description=Swaya.me Persona Backend API (Live)
  After=network.target mysql.service redis.service

  [Service]
  Type=simple
  User=vinay
  Group=vinay
  WorkingDirectory=/www/wwwroot/persona-live/backend
  Environment=PATH=/www/wwwroot/persona-live/backend/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
  Environment=PYTHONPATH=/www/wwwroot/persona-live/backend
  EnvironmentFile=/www/wwwroot/persona-live/backend/.env
  ExecStart=/www/wwwroot/persona-live/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8004 --workers 4
  Restart=on-failure
  RestartSec=5
  StandardOutput=append:/var/log/swayame-persona-live.log
  StandardError=append:/var/log/swayame-persona-live-error.log
  NoNewPrivileges=true
  PrivateTmp=true

  [Install]
  WantedBy=multi-user.target
  ```

- [ ] **8.3** Reload systemd and enable/start dev service:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable swayame-persona-dev.service
  sudo systemctl start swayame-persona-dev.service
  ```
- [ ] **8.4** Verify dev service is running:
  ```bash
  sudo systemctl status swayame-persona-dev.service
  curl -s http://127.0.0.1:8003/health
  ```

---

### Phase 9 — Nginx Configs
**Status:** `[ ] Not started`

> **SSL prerequisite:** Certs for `dev.persona.swaya.me` and `persona.swaya.me` must exist at `/www/server/panel/vhost/cert/<domain>/` before enabling HTTPS blocks. Issue via aaPanel if not already done. Start with HTTP-only if certs aren't ready.

- [ ] **9.1** Confirm SSL cert exists for dev domain:
  ```bash
  ls /www/server/panel/vhost/cert/dev.persona.swaya.me/
  ```
- [ ] **9.2** Create `/www/server/panel/vhost/nginx/dev.persona.swaya.me.conf`  
  Mirror of `test.swaya.me.conf` with these substitutions:
  - `server_name` → `dev.persona.swaya.me`
  - `root` → `/www/wwwroot/dev.persona.swaya.me/frontend/dist`
  - API proxy → `http://127.0.0.1:8003/api/`
  - SSL cert path → `/www/server/panel/vhost/cert/dev.persona.swaya.me/`
  - Access log → `/www/wwwlogs/dev.persona.swaya.me.log`
  - Error log → `/www/wwwlogs/dev.persona.swaya.me.error.log`

- [ ] **9.3** Confirm SSL cert exists for live domain:
  ```bash
  ls /www/server/panel/vhost/cert/persona.swaya.me/
  ```
- [ ] **9.4** Create `/www/server/panel/vhost/nginx/persona.swaya.me.conf`  
  Mirror of `www.swaya.me.conf` with these substitutions:
  - `server_name` → `persona.swaya.me`
  - `root` → `/www/wwwroot/persona.swaya.me`
  - API proxy → `http://127.0.0.1:8004/api/`
  - SSL cert path → `/www/server/panel/vhost/cert/persona.swaya.me/`
  - Access log → `/www/wwwlogs/persona.swaya.me.log`
  - Error log → `/www/wwwlogs/persona.swaya.me.error.log`

- [ ] **9.5** Test nginx config — must say `syntax is ok` before reloading:
  ```bash
  sudo /www/server/nginx/sbin/nginx -t
  ```
  **Stop here if the test fails. Do not reload with a broken config.**

- [ ] **9.6** Reload nginx:
  ```bash
  sudo /www/server/nginx/sbin/nginx -s reload
  ```
- [ ] **9.7** Immediately verify existing sites are still up after reload:
  ```bash
  curl -sf http://127.0.0.1:8001/health && echo "test.swaya.me OK" || echo "⛔ test.swaya.me BROKEN"
  curl -sf http://127.0.0.1:8000/health && echo "www.swaya.me OK"  || echo "⛔ www.swaya.me BROKEN"
  ```
  **If either returns BROKEN, roll back the nginx config immediately and do not continue.**

- [ ] **9.8** Verify persona dev site: `https://dev.persona.swaya.me` loads in browser

---

### Phase 10 — Persona Deploy Script
**Status:** `[ ] Not started`

- [ ] **10.1** Create `/www/wwwroot/dev.persona.swaya.me/persona-deploy.sh` with the same structure as `deploy.sh` using these config values:
  ```bash
  PERSONA_DEV_ROOT="/www/wwwroot/dev.persona.swaya.me"
  PERSONA_LIVE_ROOT="/www/wwwroot/persona-live"
  PERSONA_LIVE_FRONTEND="/www/wwwroot/persona.swaya.me"
  PERSONA_BACKUP_DIR="/home/vinay/persona-backups"
  DEV_SERVICE="swayame-persona-dev.service"
  LIVE_SERVICE="swayame-persona.service"
  ```
  Commands to implement:
  - `deploy-dev` — build frontend + restart `swayame-persona-dev.service`
  - `promote-live` — tag (`persona/release/...`), rsync backend, run migrations on `swayame_persona`, deploy frontend dist, restart live service, health check with auto-rollback
  - `rollback-live` — restore from backup
  - `migrate-dev` / `migrate-live` — alembic migrations
  - `health` — health check ports 8003 and 8004
  - `status`, `logs-dev`, `logs-live`

  > Git tags use prefix `persona/release/` to avoid collision with main app tags (`release/`).

- [ ] **10.2** Make executable: `chmod +x /www/wwwroot/dev.persona.swaya.me/persona-deploy.sh`
- [ ] **10.3** Commit `persona-deploy.sh` to the `persona` branch:
  ```bash
  git -C /www/wwwroot/dev.persona.swaya.me add persona-deploy.sh
  git -C /www/wwwroot/dev.persona.swaya.me commit -m "feat: add persona app deploy script"
  ```
- [ ] **10.4** Smoke test: `./persona-deploy.sh health`

---

## Verification Checklist (Final)
**Status:** `[ ] Not started`

- [ ] `git -C /home/vinay/Swaya.me worktree list` shows both paths on correct branches
- [ ] `git -C /home/vinay/Swaya.me branch` shows `main` and `persona`
- [ ] `curl -s http://127.0.0.1:8003/health` returns healthy response
- [ ] `https://dev.persona.swaya.me` loads the app without JS errors in browser
- [ ] Edit a file in persona worktree → `git -C /www/wwwroot/dev.persona.swaya.me status` shows dirty; `git -C /home/vinay/Swaya.me status` is clean
- [ ] `redis-cli -n 1 keys "*"` shows persona keys; `redis-cli -n 0 keys "*"` shows main app keys only
- [ ] Both `swayame-backend-test.service` (8001) and `swayame-persona-dev.service` (8003) run simultaneously without conflict
- [ ] `mysql -u swayame_user -p swayame_persona_dev -e "SHOW TABLES;"` — shows all app tables; `swayame_test` is untouched

---

## What Happens in the Persona Branch

The `persona` branch starts as a clean copy of `main`. All persona implementation work (from `personas_implementation_v9.md`) is committed only to this branch. The `main` branch continues receiving normal feature development for swaya.me independently.

To bring a fix from `main` into persona:
```bash
# From inside the persona worktree
git cherry-pick <sha-from-main>
```

---

## Execution Log

> Update this section each session. Format: `YYYY-MM-DD — Phase X.Y completed — notes`

| Date | Steps completed | Notes / Issues |
|------|----------------|----------------|
| — | — | — |
