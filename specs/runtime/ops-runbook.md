# Operations Runbook (MVP)

This document provides step-by-step instructions for setting up, running, and maintaining the Swaya.me platform.

---

## Prerequisites

### Required Software
- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Git**: 2.40+
- **Node.js**: 18+ (for local frontend development)
- **Python**: 3.11+ (for local backend development)

### Access Requirements
- OCI VM SSH access
- MySQL root/admin credentials
- Gitea repository access
- Domain DNS control (for SSL setup)

---

## Initial Setup

### Step 1: Provision OCI VM

1. Log in to Oracle Cloud Infrastructure (OCI) console
2. Create compute instance:
   - **Shape**: VM.Standard.E2.1.Micro (free tier)
   - **OS**: Ubuntu 24.04 LTS
   - **Resources**: 1 OCPU, 1 GB RAM (or higher if available)
   - **Boot Volume**: 50 GB
3. Configure network:
   - Allow ingress on ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)
4. Save SSH key pair for access

### Step 2: Connect to VM

```bash
ssh -i ~/.ssh/oci_key.pem ubuntu@<vm_public_ip>
```

### Step 3: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Step 4: Clone Repository

```bash
# Install Git (if not already installed)
sudo apt install git -y

# Clone from Gitea
git clone https://gitea.example.com/your-org/swaya.me.git
cd swaya.me
```

### Step 5: Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env with production values
nano .env
```

**Required Values**:
```bash
DB_HOST=<mysql-host-endpoint>
DB_PORT=3306
DB_NAME=swaya_db
DB_USER=admin
DB_PASSWORD=<secure_password>

JWT_SECRET=<generate_random_256_bit_secret>
ALLOWED_ORIGINS=https://swaya.me

REACT_APP_API_URL=https://swaya.me/api/v1
```

**Generate JWT Secret**:
```bash
openssl rand -hex 32
```

### Step 6: Initialize Database

```bash
# Run database migrations
docker-compose run backend alembic upgrade head

# Seed initial data (optional)
docker-compose run backend python scripts/seed_data.py
```

### Step 7: Start Services

```bash
# Build and start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 8: Configure Nginx (SSL)

```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y

# Obtain SSL certificate
sudo certbot --nginx -d swaya.me -d www.swaya.me

# Verify auto-renewal
sudo certbot renew --dry-run
```

### Step 9: Verify Deployment

```bash
# Check health endpoint
curl https://swaya.me/api/v1/health

# Expected response:
# {"status": "healthy", "timestamp": "2026-01-27T10:00:00Z"}
```

---

## Running the Platform

### Start All Services

```bash
docker-compose up -d
```

### Stop All Services

```bash
docker-compose down
```

### Restart a Single Service

```bash
docker-compose restart backend
docker-compose restart frontend
docker-compose restart redis
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

---

## Database Operations

### Run Migrations

```bash
# Upgrade to latest version
docker-compose run backend alembic upgrade head

# Downgrade one version
docker-compose run backend alembic downgrade -1

# View migration history
docker-compose run backend alembic history
```

### Create New Migration

```bash
# Auto-generate migration from model changes
docker-compose run backend alembic revision --autogenerate -m "Add new column"

# Manually create migration
docker-compose run backend alembic revision -m "Custom migration"
```

### Connect to MySQL

```bash
mysql -h <mysql-host-endpoint> -u admin -p swaya_db
```

### Backup Database

```bash
# Create backup
mysqldump -h <mysql-host-endpoint> \
  -u admin -p swaya_db > backup_$(date +%Y%m%d).sql

# Restore backup
mysql -h <mysql-host-endpoint> \
  -u admin -p swaya_db < backup_20260127.sql
```

---

## Redis Operations

### Connect to Redis CLI

```bash
docker exec -it swaya-redis redis-cli
```

### Common Redis Commands

```bash
# View all keys
KEYS *

# Get session state
GET session:sess_xyz:state

# View active sessions
SCAN 0 MATCH session:*

# Clear all keys (use with caution!)
FLUSHALL

# View memory usage
INFO memory
```

---

## Monitoring & Health Checks

### Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/api/v1/health` | Overall system health | `{"status": "healthy"}` |
| `/api/v1/ping` | Basic connectivity | `{"message": "pong"}` |

### Check Service Status

```bash
# Docker services
docker-compose ps

# Expected output:
# NAME              COMMAND                  STATUS
# swaya-backend     "uvicorn main:app"       Up
# swaya-frontend    "nginx -g 'daemon of…"   Up
# swaya-redis       "docker-entrypoint.s…"   Up
# swaya-nginx       "nginx -g 'daemon of…"   Up
```

### Monitor Resource Usage

```bash
# Docker stats
docker stats

# System resources
htop

# Disk usage
df -h

# Network connections
netstat -tuln
```

---

## Troubleshooting

### Backend Not Starting

**Check logs**:
```bash
docker-compose logs backend
```

**Common issues**:
- Database connection failed: Verify DB_HOST, DB_USER, DB_PASSWORD
- Redis connection failed: Ensure Redis container is running
- Port already in use: Stop conflicting service or change PORT

### Frontend Not Loading

**Check logs**:
```bash
docker-compose logs frontend
docker-compose logs nginx
```

**Common issues**:
- API URL incorrect: Verify REACT_APP_API_URL in .env
- Nginx misconfiguration: Check `/etc/nginx/nginx.conf`
- SSL certificate expired: Renew with `sudo certbot renew`

### Quiz Session Not Working

**Check Redis**:
```bash
docker exec -it swaya-redis redis-cli
KEYS session:*
```

**Verify session state**:
```bash
GET session:sess_xyz:state
```

**Check backend logs for errors**:
```bash
docker-compose logs backend | grep ERROR
```

### Database Connection Issues

**Test connection**:
```bash
mysql -h $DB_HOST -u $DB_USER -p -e "SELECT 1;"
```

**Check MySQL service**:
```bash
sudo systemctl status mysql
```

**Verify credentials**:
```bash
docker-compose run backend python -c "from config import settings; print(settings.database_url)"
```

---

## Maintenance Tasks

### Update Application Code

```bash
# Pull latest code
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose build
docker-compose up -d

# Run migrations (if needed)
docker-compose run backend alembic upgrade head
```

### Clear Redis Cache

```bash
docker exec -it swaya-redis redis-cli FLUSHALL
```

### Rotate JWT Secret (Post-MVP)

1. Update `JWT_SECRET` in `.env`
2. Restart backend: `docker-compose restart backend`
3. **Note**: All existing tokens will be invalidated (users must re-login)

### SSL Certificate Renewal

```bash
# Automatic renewal (runs via cron)
sudo certbot renew

# Manual renewal
sudo certbot renew --force-renewal
```

---

## Seed Data (Development/Testing)

### Create Test Host User

```bash
docker-compose run backend python scripts/seed_data.py
```

**Script contents** (scripts/seed_data.py):
```python
from sqlalchemy.orm import Session
from backend.database import engine, Base
from backend.models import User
import bcrypt
import uuid

Base.metadata.create_all(bind=engine)
session = Session(engine)

# Create test host
password_hash = bcrypt.hashpw("password123".encode(), bcrypt.gensalt(12)).decode()
user = User(
    user_id=str(uuid.uuid4()),
    email="host@example.com",
    password_hash=password_hash,
    full_name="Test Host"
)
session.add(user)
session.commit()
print("Test host created: host@example.com / password123")
```

---

## Backup & Recovery

### Full System Backup

```bash
# Backup database
mysqldump -h $DB_HOST -u $DB_USER -p swaya_db > backup_db_$(date +%Y%m%d).sql

# Backup application code
tar -czf backup_code_$(date +%Y%m%d).tar.gz /path/to/swaya.me

# Backup environment config
cp .env backup_env_$(date +%Y%m%d)
```

### Disaster Recovery

1. Provision new OCI VM
2. Install Docker and Docker Compose
3. Clone repository
4. Restore `.env` file
5. Restore database backup
6. Run migrations
7. Start services

---

## Performance Tuning (Post-MVP)

### Database Connection Pooling

```bash
# Increase pool size for high load
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

### Redis Max Connections

```bash
REDIS_MAX_CONNECTIONS=100
```

### Nginx Worker Processes

```nginx
# In nginx.conf
events {
    worker_connections 2048;
}
```

---

## Security Checklist

- [ ] JWT secret is strong (256-bit random)
- [ ] Database password is strong
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Firewall rules: only ports 22, 80, 443 exposed
- [ ] SSH key-based authentication (no password login)
- [ ] Redis protected (localhost only, or password-protected)
- [ ] CORS configured (no wildcard origins)
- [ ] Rate limiting enabled
- [ ] Logs monitored for suspicious activity
