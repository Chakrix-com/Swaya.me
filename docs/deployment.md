# Deployment

This guide covers production deployment on a Linux server. Swaya runs without Docker in production — it uses Nginx as a reverse proxy and systemd for process supervision.

---

## Prerequisites

- Linux server (Ubuntu 22.04+ or similar)
- Python 3.10+
- Node.js 20+ and npm
- MySQL 8
- Redis 7
- Nginx
- Git

---

## Initial Server Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Chakrix-com/Swaya.me.git /opt/swaya
cd /opt/swaya
```

### 2. Python Virtual Environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`. Required variables:

| Variable | Description |
|---|---|
| `DB_HOST` | MySQL host (usually `localhost`) |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `REDIS_HOST` | Redis host (usually `localhost`) |
| `REDIS_PORT` | Redis port (default `6379`) |
| `JWT_SECRET` | Long random string — generate with `openssl rand -hex 32` |
| `FRONTEND_URL` | Public URL of the app (e.g., `https://www.swaya.me`) |
| `GEMINI_KEY` | Google AI Studio API key (for AI features) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID (for Google login) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (587 for STARTTLS) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `SMTP_FROM_EMAIL` | Sender email address |
| `SMTP_FROM_NAME` | Sender display name |

Optional:

| Variable | Description |
|---|---|
| `OLLAMA_BASE_URL` | Local Ollama endpoint for offline AI |
| `UPLOADS_BASE_DIR` | Path for uploaded files (default: `backend/uploads`) |

### 4. Database Setup

Create the MySQL database and user:

```sql
CREATE DATABASE swaya CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'swaya'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON swaya.* TO 'swaya'@'localhost';
FLUSH PRIVILEGES;
```

Run Alembic migrations:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### 5. Seed Initial Data (Optional)

```bash
python scripts/seed_data.py
```

This creates the default super_admin tenant and a first admin user.

---

## Frontend Build

```bash
cd frontend
npm install
npm run build
```

The production build is output to `frontend/dist/`. This directory is served directly by Nginx.

---

## Systemd Service

Create `/etc/systemd/system/swayame-backend.service`:

```ini
[Unit]
Description=Swaya.me FastAPI Backend
After=network.target mysql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/swaya/backend
Environment="PATH=/opt/swaya/backend/.venv/bin"
ExecStart=/opt/swaya/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable swayame-backend
sudo systemctl start swayame-backend
sudo systemctl status swayame-backend
```

---

## Nginx Configuration

```nginx
server {
    listen 80;
    server_name www.swaya.me;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.swaya.me;

    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    # Serve frontend static files
    root /opt/swaya/frontend/dist;
    index index.html;

    # SPA fallback — all non-asset requests serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API to FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Required for SSE (Server-Sent Events) — disable buffering
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_http_version 1.1;
    }

    # Static file uploads (images only — not proctoring snapshots)
    location /api/uploads/ {
        alias /opt/swaya/backend/uploads/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
}
```

Test and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Deploying Updates

### Backend Update

```bash
cd /opt/swaya
git pull

cd backend
source .venv/bin/activate
pip install -r requirements.txt   # only if requirements changed
alembic upgrade head               # only if migrations added

sudo systemctl restart swayame-backend
```

### Frontend Update

```bash
cd /opt/swaya/frontend
npm install    # only if package.json changed
npm run build
# Nginx serves the new dist/ immediately — no restart needed
```

---

## Database Migrations

Migrations live in `backend/persistence/migrations/`. Naming convention: `YYYYMMDD_HHMM_description.py`.

**Always run migrations before restarting the backend** when deploying a version that includes schema changes:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
sudo systemctl restart swayame-backend
```

**Creating a new migration:**

```bash
alembic revision --autogenerate -m "add_column_to_quiz"
# Review the generated file in persistence/migrations/versions/
# Then rename it to follow the date-based convention
```

Always review auto-generated migrations before applying — autogenerate can miss complex changes (custom types, multi-step transforms).

---

## Logs

```bash
# Backend logs
sudo journalctl -u swayame-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

---

## Health Check

```bash
curl https://www.swaya.me/api/health
# → {"status": "ok"}
```

---

## Redis

Redis should be configured with a password in production. Update `REDIS_PASSWORD` in `backend/.env`. The default configuration (no auth, localhost only) is acceptable for single-host deployments with a firewall blocking external Redis access.

For persistence, enable `appendonly yes` in `redis.conf` to survive server restarts without losing the JWT blocklist or active OTPs.
