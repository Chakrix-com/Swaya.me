# Swaya.me Deployment Guide

Last updated: 2026-03-09

## Overview

`deploy.sh` is the single entrypoint for all deployment operations. It manages two environments:

| Environment | Domain | Backend port | DB |
|---|---|---|---|
| Test/Dev | `test.swaya.me` | 8001 | `swayame_test` |
| Live/Production | `www.swaya.me` | 8000 | `swayame` |

---

## Quick Start

```bash
./deploy.sh          # interactive menu
./deploy.sh <cmd>    # run a specific command directly
```

---

## Normal Dev → Live Flow

```
# 1. Do your dev work, commit to main
git add ... && git commit -m "feat: ..."

# 2. Deploy to test and verify
./deploy.sh deploy-test
# Check https://test.swaya.me visually (noVNC: http://www.swaya.me:7900)

# 3. Run mandatory regression gate on test environment
BASE_URL=https://test.swaya.me/api/v1 \
APP_BASE_URL=https://test.swaya.me \
HOST_EMAIL=demo@swaya.me \
HOST_PASSWORD=Demo1234 \
bash scripts/regression/run_preprod_gate.sh
# Optional for high-risk releases:
# RUN_EXTENDED=1 bash scripts/regression/run_preprod_gate.sh

# 4. Promote to production
./deploy.sh promote-live
```

---

## Commands

| Command | Description |
|---|---|
| `deploy-test` | Build frontend + restart test backend + health check |
| `promote-live` | Tag + backup + sync + migrate + deploy + health check |
| `rollback-live` | Restore a past release on live |
| `hotfix` | Branch off a past release tag for a targeted fix |
| `releases` | List all release tags with metadata |
| `migrate-test` | Run alembic migrations on test DB |
| `migrate-live` | Run alembic migrations on live DB |
| `health` | Health-check both environments |
| `status` | Show systemd service status |
| `logs-test` | Tail test backend logs |
| `logs-live` | Tail live backend logs |

---

## How promote-live Works

1. Checks git working tree — warns if uncommitted changes exist (they won't be in the release tag)
2. Creates an **annotated git tag** `release/YYYYMMDD_HHMMSS` on current HEAD
3. **Backs up** current live frontend (`/www/wwwroot/www.swaya.me`) and backend (`/www/wwwroot/swaya-live/backend`) to `/home/vinay/swaya-backups/`
4. Saves a `.meta` file alongside the backup (tag, SHA, branch, date, backup paths)
5. `rsync` backend code to `/www/wwwroot/swaya-live/backend/` (excludes `.env`, `.venv/`, `uploads/`)
6. Reinstalls pip dependencies if `requirements.txt` changed
7. Runs `alembic upgrade head` on the live DB (`swayame`)
8. Copies `frontend/dist/` to `/www/wwwroot/www.swaya.me/`
9. Restarts `swayame-backend.service` + reloads nginx
10. Health check → **auto-rollback** if the health check fails

---

## Going Back

### Rollback live (something broke after promote)

```bash
./deploy.sh rollback-live
```

Lists all past releases. Select one to restore. The script:
- Restores frontend from the **file backup** for that release
- Restores backend from the **file backup** (falls back to `git archive <tag>` if no file backup exists)
- Restarts live backend + health check

### Hotfix (need to fix a specific old release)

Use this when `main` has moved on but you need to patch a specific deployed version:

```bash
./deploy.sh hotfix
# Select the release to branch from
# Enter a branch name (e.g. hotfix/20260309)
```

This runs `git checkout -b hotfix/xxx release/YYYYMMDD_HHMMSS`. Make your fix, then:

```bash
./deploy.sh deploy-test     # test the fix
./deploy.sh promote-live    # promote hotfix to live
git checkout main
git merge hotfix/xxx        # bring the fix back into main
```

---

## Git Release Tags

Every `promote-live` creates an annotated tag:

```
release/20260309_143022
```

View all releases:

```bash
git tag -l "release/*" --sort=-creatordate
./deploy.sh releases        # same, with backup status
```

Inspect a specific release:

```bash
git show release/20260309_143022
```

---

## Backups

Stored at `/home/vinay/swaya-backups/`:

```
swaya-backups/
├── frontend_release/20260309_143022/   # snapshot of /www/wwwroot/www.swaya.me
├── backend_release/20260309_143022/    # snapshot of live backend code (no .venv/.env/uploads)
└── release/20260309_143022.meta        # tag, SHA, branch, date, backup paths
```

Backups accumulate over time. Clean old ones manually when disk space is a concern.

---

## Safety Rules

- `.env`, `.venv/`, and `uploads/` are **never overwritten** by rsync — live secrets and data are always preserved
- `promote-live` and `migrate-live` require explicit `y` confirmation
- `promote-live` must only be run after a successful regression gate run on test (`scripts/regression/run_preprod_gate.sh`)
- Auto-rollback triggers if the post-deploy health check fails
- Dirty working tree on `promote-live` is a warning, not a hard block — but uncommitted changes won't be in the git tag

---

## Paths Reference

| Path | Purpose |
|---|---|
| `/home/vinay/Swaya.me/` | Dev repo (test environment source) |
| `/home/vinay/Swaya.me/frontend/dist/` | Built frontend (used by both test and live deploy) |
| `/www/wwwroot/swaya-live/backend/` | Live backend code |
| `/www/wwwroot/www.swaya.me/` | Live frontend files served by nginx |
| `/home/vinay/swaya-backups/` | Release backups |
| `/etc/systemd/system/swayame-backend.service` | Live backend service |
| `/etc/systemd/system/swayame-backend-test.service` | Test backend service |
| `/www/server/panel/vhost/nginx/www.swaya.me.conf` | Live nginx vhost |
| `/www/server/panel/vhost/nginx/test.swaya.me.conf` | Test nginx vhost |
